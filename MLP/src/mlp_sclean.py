import numpy as np  # Библиотека для работы с массивами и математическими операциями
from sklearn.model_selection import train_test_split  # Функция для разделения данных на обучающую и тестовую выборки
from sklearn.neural_network import MLPClassifier  # Класс многослойного перцептрона для классификации
from sklearn.datasets import make_classification  # Функция для генерации синтетических данных для задач классификации
from sklearn.metrics import accuracy_score  # Функция для вычисления метрики точности (accuracy)
from sklearn.preprocessing import StandardScaler  # Класс для масштабирования (стандартизации) данных

# --- Шаг 1: Генерация синтетических данных ---
# Создаем набор данных для задачи бинарной классификации.
# n_samples: общее количество образцов (точек данных).
# n_features: общее количество признаков (размерность входных данных).
# n_informative: количество информативных признаков (тех, что действительно влияют на класс).
# n_redundant: количество избыточных признаков (линейные комбинации информативных).
# n_classes: количество классов для классификации (здесь 2, т.е. бинарная классификация).
# random_state: сид для генератора случайных чисел для воспроизводимости результатов.
X, y = make_classification(n_samples=500, n_features=20, n_informative=15,
                           n_redundant=5, n_classes=2, random_state=42)
# X: массив признаков (форма: [n_samples, n_features])
# y: массив меток классов (форма: [n_samples,])

# --- Шаг 2: Разделение данных на обучающую и тестовую выборки ---
# Делим исходный набор данных на две части:
# - Обучающая выборка (X_train, y_train): используется для обучения модели.
# - Тестовая выборка (X_test, y_test): используется для оценки производительности обученной модели на новых данных.
# test_size=0.3: доля данных, которая пойдет в тестовую выборку (здесь 30%).
# random_state=42: обеспечивает одинаковое разделение при каждом запуске кода.
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

# --- Шаг 3: Масштабирование (стандартизация) данных ---
# Масштабирование важно для MLP, так как они чувствительны к масштабу признаков.
# StandardScaler преобразует данные так, чтобы они имели среднее значение 0 и стандартное отклонение 1.
scaler = StandardScaler()
# Вычисляем среднее и стандартное отклонение НА ОБУЧАЮЩЕЙ ВЫБОРКЕ и применяем к ней масштабирование.
X_train = scaler.fit_transform(X_train)
# Применяем ТО ЖЕ САМОЕ масштабирование (с параметрами, вычисленными на X_train) к ТЕСТОВОЙ ВЫБОРКЕ.
# Это важно, чтобы избежать "утечки данных" из тестовой выборки в процесс обучения.
X_test = scaler.transform(X_test)

# --- Шаг 4: Создание модели MLPClassifier ---
# Инициализируем модель многослойного перцептрона с заданными параметрами.
mlp = MLPClassifier(
    # hidden_layer_sizes: определяет архитектуру скрытых слоев.
    # Кортеж (100, 50) означает ДВА скрытых слоя:
    # первый слой со 100 нейронами, второй слой с 50 нейронами.
    hidden_layer_sizes=(100, 50),

    # activation: функция активации для нейронов в скрытых слоях.
    # 'relu' (Rectified Linear Unit) - популярный выбор. Другие варианты: 'tanh', 'logistic'.
    activation='relu',

    # solver: алгоритм оптимизации весов нейронной сети.
    # 'adam' - эффективный оптимизатор, хорошо работает на больших наборах данных.
    # Другие варианты: 'sgd' (стохастический градиентный спуск), 'lbfgs'.
    solver='adam',

    # alpha: параметр L2-регуляризации (штраф за большие веса).
    # Помогает предотвратить переобучение модели. Большее значение -> сильнее регуляризация.
    alpha=0.0001,

    # max_iter: максимальное количество итераций (эпох) обучения.
    # Обучение остановится, если достигнет этого числа или если сработает early_stopping.
    max_iter=500,

    # random_state: сид для инициализации весов и других случайных процессов.
    # Обеспечивает воспроизводимость результатов обучения модели.
    random_state=42,

    # early_stopping: флаг для включения ранней остановки.
    # Если True, модель откладывает часть обучающих данных как валидационную выборку.
    # Обучение прекращается, если метрика на валидационной выборке не улучшается в течение
    # определенного числа итераций (n_iter_no_change), что помогает предотвратить переобучение.
    early_stopping=True,

    # verbose: флаг для вывода информации о процессе обучения.
    # Если True, будет выводиться значение функции потерь на каждой итерации.
    verbose=False
)

# --- Шаг 5: Обучение модели ---
# Запускаем процесс обучения модели на обучающих данных (X_train, y_train).
# Модель будет итеративно подстраивать свои веса, чтобы минимизировать функцию потерь.
print("Обучение модели MLPClassifier...")
mlp.fit(X_train, y_train)
print("Обучение завершено.")

# --- Шаг 6: Предсказание на тестовых данных ---
# Используем обученную модель для предсказания меток классов для тестовой выборки (X_test).
# Модель применяет свои выученные веса к входным данным X_test.
y_pred = mlp.predict(X_test)

# --- Шаг 7: Оценка модели ---
# Сравниваем предсказанные метки (y_pred) с истинными метками (y_test)
# и вычисляем точность (accuracy) - долю правильных предсказаний.
accuracy = accuracy_score(y_test, y_pred)
# Выводим результат точности, отформатированный до двух знаков после запятой.
print(f"Точность модели на тестовых данных: {accuracy:.2f}")

# --- Дополнительно: получение вероятностей классов ---
# Метод predict_proba возвращает вероятности принадлежности каждого образца к каждому классу.
# Для бинарной классификации это будет массив формы [n_samples, 2],
# где первый столбец - вероятность класса 0, второй - вероятность класса 1.
# probabilities = mlp.predict_proba(X_test)
# print("Вероятности классов для первых 5 примеров:\n", probabilities[:5])