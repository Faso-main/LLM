import pandas as pd
import torch, json, os
import numpy as np
from torch.utils.data import Dataset, DataLoader
from transformers import T5Tokenizer, T5ForConditionalGeneration, AdamW
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, f1_score, recall_score
from tqdm import tqdm
import matplotlib.pyplot as plt
import time
import psutil

# Конфигурация
MODEL_NAME = 't5-small'  # Используем T5-small
BATCH_SIZE = 8  
MAX_LEN = 128
EPOCHS = 5     
LEARNING_RATE = 2e-5

SAVE_PATH = os.path.join('NLP_Med', 'trained', f'fake_{MODEL_NAME}_{EPOCHS}ep')
MARKED_PATH = os.path.join('NLP_Med', 'src', 'fake_marked.json')
LABLE_PATH = os.path.join('NLP_Med', 'src', 'label2id.json')
RESULTS_PATH = os.path.join('NLP_Med', 'src', 'results', f'fake_{MODEL_NAME}_{EPOCHS}ep.csv')

# 1. Загрузка и подготовка данных
def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    texts = df['текст'].tolist()
    labels = df['классификация'].tolist()  
    
    # Преобразование меток в текстовый формат (T5 работает с текстом)
    unique_labels = sorted(list(set(labels)))
    label2id = {label: idx for idx, label in enumerate(unique_labels)}
    id2label = {idx: label for label, idx in label2id.items()}
    labels = [label2id[label] for label in labels]
    
    # Сохранение меток
    with open(LABLE_PATH, 'w') as f:
        json.dump(label2id, f)
    
    return train_test_split(texts, labels, test_size=0.2, random_state=42), id2label

# 2. Создание Dataset
class MedicalDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = str(self.labels[idx])  # Преобразуем метку в строку
        
        # Кодируем текст и метку
        encoding = self.tokenizer(
            text,
            max_length=self.max_len,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        target_encoding = self.tokenizer(
            label,
            max_length=10,  # Максимальная длина метки
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': target_encoding['input_ids'].flatten()  # Используем input_ids для меток
        }

# 3. Обучение модели
def train_epoch(model, dataloader, optimizer, device, scheduler=None):
    model.train()
    total_loss = 0
    progress_bar = tqdm(dataloader, desc='Training', leave=False)
    
    for batch in progress_bar:
        optimizer.zero_grad()
        
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['labels'].to(device)
        
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
        loss = outputs.loss
        total_loss += loss.item()
        
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        if scheduler:
            scheduler.step()
        
        progress_bar.set_postfix({'loss': loss.item()})
    
    return total_loss / len(dataloader)

# 4. Валидация
def eval_model(model, dataloader, device, id2label, tokenizer):
    model.eval()
    predictions = []
    true_labels = []
    
    with torch.no_grad():
        for batch in tqdm(dataloader, desc='Validation', leave=False):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)
            
            # Генерация предсказаний
            generated_ids = model.generate(input_ids=input_ids, attention_mask=attention_mask, max_length=10)
            preds = [tokenizer.decode(g_id, skip_special_tokens=True) for g_id in generated_ids]
            true = [tokenizer.decode(t_id, skip_special_tokens=True) for t_id in labels]
            
            predictions.extend(preds)
            true_labels.extend(true)
    
    # Преобразование текстовых меток в числовые
    # Заменяем пустые строки на значение по умолчанию (например, 0)
    predictions = [int(label) if label.strip() != '' else 0 for label in predictions]
    true_labels = [int(label) for label in true_labels]
    
    # Генерация отчета
    print("\nClassification Report:")
    report = classification_report(
        true_labels, 
        predictions, 
        target_names=list(id2label.values()),
        zero_division=0,
        labels=list(range(len(id2label))),
        output_dict=True
    )
    print(classification_report(
        true_labels, 
        predictions, 
        target_names=list(id2label.values()),
        zero_division=0,
        labels=list(range(len(id2label)))
    ))
    
    # Использование памяти
    memory_usage = psutil.Process().memory_info().rss / 1024 ** 2  # в МБ
    
    # Извлечение F1 и Recall
    f1 = report['weighted avg']['f1-score']
    recall = report['weighted avg']['recall']
    
    return accuracy_score(true_labels, predictions), f1, recall, memory_usage

# 5. Прогнозирование
class MedicalClassifier:
    def __init__(self, model_path, label2id_path):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = T5ForConditionalGeneration.from_pretrained(model_path).to(self.device)
        self.tokenizer = T5Tokenizer.from_pretrained(model_path)
        
        with open(label2id_path) as f:
            self.label2id = json.load(f)
            self.id2label = {v: k for k, v in self.label2id.items()}
    
    def predict(self, text):
        self.model.eval()
        encoding = self.tokenizer(
            text,
            max_length=MAX_LEN,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        ).to(self.device)
        
        with torch.no_grad():
            generated_ids = self.model.generate(**encoding, max_length=10)
        
        pred_label = self.tokenizer.decode(generated_ids[0], skip_special_tokens=True)
        return {
            'class': self.id2label[int(pred_label)],
            'confidence': 1.0  # T5 не возвращает вероятности, поэтому используем 1.0
        }

# Основной пайплайн
def main():
    # Загрузка данных
    (train_texts, val_texts, train_labels, val_labels), id2label = load_data(MARKED_PATH)
    
    # Инициализация модели
    tokenizer = T5Tokenizer.from_pretrained(MODEL_NAME)
    model = T5ForConditionalGeneration.from_pretrained(MODEL_NAME)
    
    # Создание DataLoader
    train_dataset = MedicalDataset(train_texts, train_labels, tokenizer, MAX_LEN)
    val_dataset = MedicalDataset(val_texts, val_labels, tokenizer, MAX_LEN)
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, num_workers=2)
    
    # Настройка устройства и оптимизатора
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    
    optimizer = AdamW(model.parameters(), lr=LEARNING_RATE, correct_bias=False)
    scheduler = torch.optim.lr_scheduler.LinearLR(optimizer, total_iters=EPOCHS)
    
    # Список для хранения результатов
    results = []
    
    # Цикл обучения
    best_acc = 0
    for epoch in range(EPOCHS):
        print(f'\nEpoch {epoch + 1}/{EPOCHS}')
        start_time = time.time()
        train_loss = train_epoch(model, train_loader, optimizer, device, scheduler)
        val_acc, f1, recall, memory_usage = eval_model(model, val_loader, device, id2label, tokenizer)
        epoch_time = time.time() - start_time
        
        # Сохранение результатов
        results.append({
            'epoch': epoch + 1,
            'train_loss': train_loss,
            'val_accuracy': val_acc,
            'f1_score': f1,
            'recall': recall,
            'epoch_time': epoch_time,
            'memory_usage': memory_usage
        })
        
        # Сохранение лучшей модели
        if val_acc > best_acc:
            best_acc = val_acc
            model.save_pretrained(SAVE_PATH)
            tokenizer.save_pretrained(SAVE_PATH)
            print(f"New best model saved with accuracy {val_acc:.4f}")
        
        print(f'Train Loss: {train_loss:.4f} | Val Accuracy: {val_acc:.4f} | F1 Score: {f1:.4f} | Recall: {recall:.4f} | Epoch Time: {epoch_time:.2f}s | Memory Usage: {memory_usage:.2f}MB')
    
    print("\nTraining completed!")
    
    # Сохранение результатов в CSV
    results_df = pd.DataFrame(results)
    results_df.to_csv(RESULTS_PATH, index=False)
    print(f"Results saved to {RESULTS_PATH}")
    
    # Построение графика точности валидации
    plt.figure(figsize=(10, 6))
    plt.plot(results_df['epoch'], results_df['val_accuracy'], marker='o', linestyle='-', color='b')
    plt.title('Validation Accuracy over Epochs')
    plt.xlabel('Epoch')
    plt.ylabel('Validation Accuracy')
    plt.grid(True)
    plt.xticks(range(1, EPOCHS + 1))
    plt.show()

if __name__ == '__main__':
    main()