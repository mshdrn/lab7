import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# =====================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ И НАСТРОЙКИ ВАРИАНТА №51
# =====================================================================
df_raw = None
df_work = None
fig = plt.Figure(figsize=(10, 5.5), dpi=100)
canvas = None
current_chart = "line"
metric_frame = None  # Контейнер для динамического скрытия метрики

STUDENT_INFO = "Обухов М.С. | Группа: ИВТб-1302 | Вариант: №51"

plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans']
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid")


# =====================================================================
# ЭТАП 2. ПРЕДОБРАБОТКА
# =====================================================================
def load_data():
    global df_raw
    try:
        df_raw = pd.read_csv('data.csv')
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось загрузить data.csv\n{e}")
        exit()


def preprocess_data():
    df = df_raw.copy()

    df['ts'] = df['ts'].astype('int32')
    df['ch_id'] = df['ch_id'].astype('int16')

    df['viewers'] = df['viewers'].clip(lower=0).astype('uint16')
    df['bit'] = df['bit'].clip(lower=0.1).astype('float32')
    df['drops'] = df['drops'].clip(0.0, 100.0).astype('float32')
    df['eng'] = df['eng'].astype('float32')

    df = df.sort_values('ts').reset_index(drop=True)

    df['datetime'] = pd.to_datetime(df['ts'], unit='s')

    # Порядок дней для тепловой карты
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df['day_of_week'] = pd.Categorical(df['datetime'].dt.day_name(), categories=day_order, ordered=True)

    df['hour'] = df['datetime'].dt.hour

    df['moving_avg_viewers'] = df['viewers'].rolling(window=50, min_periods=1).mean()
    df['cdn_instability'] = df['drops'].diff().fillna(0.0)
    df['bit_per_viewer'] = np.where(df['viewers'] > 0, df['bit'] / df['viewers'], 0.0)

    bins = [-1, 6, 12, 18, 24]
    labels = ['Ночь', 'Утро', 'День', 'Вечер']
    df['time_of_day'] = pd.cut(df['hour'], bins=bins, labels=labels)

    return df


def get_filtered_data():
    """Динамический фильтр: только срез по строкам"""
    df = df_work.copy()

    try:
        start_idx = int(start_row_var.get())
        start_idx = max(0, start_idx)
    except ValueError:
        start_idx = 0

    try:
        limit_str = num_rows_var.get()
        if limit_str.lower() == "100000" or limit_str.strip() == "":
            limit = len(df)
        else:
            limit = int(limit_str)
            limit = max(1, limit)
    except ValueError:
        limit = len(df)

    df = df.iloc[start_idx: start_idx + limit]
    return df


# =====================================================================
# ЭТАП 4. ИНТЕРАКТИВНЫЕ ГРАФИКИ
# =====================================================================
def plot_line():
    global current_chart
    current_chart = "line"

    if metric_frame: metric_frame.pack_forget()

    fig.clear()
    df = get_filtered_data()
    if df.empty: return

    df_time = df.set_index('datetime').resample('5Min').mean(numeric_only=True).dropna(subset=['viewers']).reset_index()
    if df_time.empty: return

    ax = fig.add_subplot(111)
    sns.lineplot(data=df_time, x='datetime', y='viewers', ax=ax, alpha=0.3, label='Сырой поток зрителей')
    sns.lineplot(data=df_time, x='datetime', y='moving_avg_viewers', ax=ax, color='blue', linewidth=2,
                 label='Сглаженная аудитория (k=50)')

    ax.set_title("Анализ трендов аудитории трансляций")
    ax.set_ylabel("Количество зрителей")
    ax.tick_params(axis='x', rotation=30)
    fig.tight_layout()
    canvas.draw_idle()


def plot_bar():
    global current_chart
    current_chart = "bar"

    # Показываем выбор метрики только для столбчатой диаграммы
    if metric_frame: metric_frame.pack(side=tk.LEFT)

    fig.clear()
    df = get_filtered_data()
    if df.empty: return

    df_ch = df.groupby('ch_id').agg({'viewers': 'mean', 'bit': 'max'}).reset_index()
    metric = agg_filter_var.get()
    ax = fig.add_subplot(111)

    if metric == "Средние зрители":
        df_ch = df_ch.sort_values('viewers', ascending=False).head(15)
        sns.barplot(data=df_ch, x='ch_id', y='viewers', hue='ch_id', palette='coolwarm', ax=ax, legend=False)
        ax.set_title("Популярность трансляций: Среднее кол-во зрителей по каналам (Top-15)")
        ax.set_ylabel("Среднее число зрителей")
    else:
        df_ch = df_ch.sort_values('bit', ascending=False).head(15)
        sns.barplot(data=df_ch, x='ch_id', y='bit', hue='ch_id', palette='flare', ax=ax, legend=False)
        ax.set_title("Требования к сети: Максимальный битрейт по каналам (Top-15)")
        ax.set_ylabel("Макс. битрейт (Мбит/с)")

    ax.set_xlabel("ID Канала (ch_id)")
    fig.tight_layout()
    canvas.draw_idle()


def plot_scatter():
    global current_chart
    current_chart = "scatter"

    # Скрываем выбор метрики
    if metric_frame: metric_frame.pack_forget()

    fig.clear()
    df = get_filtered_data()
    if df.empty: return

    if len(df) > 3000:
        df = df.sample(3000, random_state=42)

    ax = fig.add_subplot(111)
    sns.scatterplot(data=df, x='bit_per_viewer', y='eng', hue='time_of_day',
                    size='drops', sizes=(10, 200), alpha=0.6, ax=ax, edgecolor=None)

    ax.set_title("Влияние выделенного битрейта на вовлеченность (eng)")
    ax.set_xlabel("Битрейт на одного зрителя (Мбит/с)")
    ax.set_ylabel("Индекс вовлеченности (eng)")
    fig.tight_layout()
    canvas.draw_idle()


def plot_heat_map():
    global current_chart
    current_chart = "heatmap"

    # Скрываем выбор метрики
    if metric_frame: metric_frame.pack_forget()

    fig.clear()
    df = get_filtered_data()
    if df.empty: return

    df['abs_instability'] = df['cdn_instability'].abs()
    pivot = df.pivot_table(index='day_of_week', columns='hour', values='abs_instability', aggfunc='mean',
                           observed=True)
    if pivot.empty: return

    ax = fig.add_subplot(111)
    sns.heatmap(pivot, cmap='YlOrRd', annot=False, ax=ax, cbar_kws={'label': 'Ср. колебание потерь пакетов (%)'})
    ax.set_title("Тепловая карта нестабильности CDN-сети (Сдвиг дельты потерь пакетов)")
    ax.set_xlabel("Час дня")
    ax.set_ylabel("День недели")

    fig.tight_layout()
    canvas.draw_idle()


# =====================================================================
# ИНТЕРФЕЙС И УПРАВЛЕНИЕ (TKINTER)
# =====================================================================
def refresh_data(event=None):
    if current_chart == "line":
        plot_line()
    elif current_chart == "bar":
        plot_bar()
    elif current_chart == "scatter":
        plot_scatter()
    elif current_chart == "heatmap":
        plot_heat_map()


def export_plot():
    filepath = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("PDF", "*.pdf")])
    if filepath:
        fig.savefig(filepath, dpi=300, bbox_inches='tight')
        messagebox.showinfo("Успех", "График успешно сохранен!")


def main():
    global df_work, canvas, agg_filter_var, start_row_var, num_rows_var, metric_frame

    load_data()
    df_work = preprocess_data()

    root = tk.Tk()
    root.title(f"Дашборд | {STUDENT_INFO}")
    root.geometry("1250x780")
    root.configure(bg="#f8f9fa")

    ctrl_frame = tk.Frame(root, bg="#e9ecef", pady=5, padx=10)
    ctrl_frame.pack(fill=tk.X, side=tk.TOP)

    row1 = tk.Frame(ctrl_frame, bg="#e9ecef")
    row1.pack(fill=tk.X, pady=2)
    row2 = tk.Frame(ctrl_frame, bg="#e9ecef")
    row2.pack(fill=tk.X, pady=2)

    # --- СТРОКА 1: Выбор графиков и системные кнопки ---
    tk.Label(row1, text="Вид графика:", bg="#e9ecef", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 5))
    tk.Button(row1, text="Окно k=50 (viewers, ts)", command=plot_line, width=22).pack(side=tk.LEFT, padx=2)
    tk.Button(row1, text="Группы ch_id (viewers, bit)", command=plot_bar, width=25).pack(side=tk.LEFT, padx=2)
    tk.Button(row1, text="Ratio (bit, eng, drops)", command=plot_scatter, width=22).pack(side=tk.LEFT, padx=2)
    tk.Button(row1, text="Нестабильность (drops, ts)", command=plot_heat_map, width=25).pack(side=tk.LEFT, padx=2)

    tk.Button(row1, text="💾 Сохранить", command=export_plot, width=10, bg="#d4edda").pack(side=tk.RIGHT, padx=5)
    tk.Button(row1, text="🔄 Обновить", command=refresh_data, width=10, bg="#cce5ff").pack(side=tk.RIGHT, padx=5)

    # --- СТРОКА 2: Фильтры и срезы данных ---
    tk.Label(row2, text="Фильтры:", bg="#e9ecef", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 5))

    tk.Label(row2, text="Старт со строки (index):", bg="#e9ecef").pack(side=tk.LEFT)
    start_row_var = tk.StringVar(value="0")
    start_entry = tk.Entry(row2, textvariable=start_row_var, width=8)
    start_entry.pack(side=tk.LEFT, padx=2)
    start_entry.bind("<Return>", refresh_data)

    tk.Label(row2, text="  |  Кол-во строк (limit):", bg="#e9ecef").pack(side=tk.LEFT)
    num_rows_var = tk.StringVar(value="100000")  # Оптимально для быстрого старта 2млн строк
    num_entry = tk.Entry(row2, textvariable=num_rows_var, width=8)
    num_entry.pack(side=tk.LEFT, padx=2)
    num_entry.bind("<Return>", refresh_data)

    # Создаем изолированный контейнер для метрики (по умолчанию скрыт, т.к. первый график — линейный)
    metric_frame = tk.Frame(row2, bg="#e9ecef")
    tk.Label(metric_frame, text="  |  Метрика (viewers/bit):", bg="#e9ecef").pack(side=tk.LEFT)
    agg_filter_var = tk.StringVar(value="Средние зрители")
    agg_combo = ttk.Combobox(metric_frame, textvariable=agg_filter_var,
                             values=["Средние зрители", "Максимальный битрейт"],
                             width=18, state="readonly")
    agg_combo.pack(side=tk.LEFT, padx=2)
    agg_combo.bind("<<ComboboxSelected>>", refresh_data)

    # Область отрисовки графика
    plot_frame = tk.Frame(root, bg="white", relief=tk.SUNKEN, bd=1)
    plot_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    toolbar = NavigationToolbar2Tk(canvas, plot_frame)
    toolbar.update()
    toolbar.pack(side=tk.TOP, fill=tk.X)

    plot_line()  # Запуск первого графика (метрика скроется автоматически)
    root.mainloop()


if __name__ == "__main__":
    main()
