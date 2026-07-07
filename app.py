import os
import sqlite3
from datetime import datetime
from flask import Flask, request, render_template_string, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'math_check_secret_key_change_me'

# Конфигурация
ADMIN_PASSWORD = 'math123'  # Пароль для входа в админку
UPLOAD_FOLDER = 'uploads'
DATABASE = 'mathcheck.db'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Создаем папку для PDF, если её нет
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Инициализация базы данных
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        # Таблица домашних заданий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS homeworks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                pdf_filename TEXT NOT NULL,
                correct_answers TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        # Таблица результатов учеников
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                homework_id INTEGER,
                student_name TEXT NOT NULL,
                student_answers TEXT NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                percentage REAL NOT NULL,
                submitted_at TEXT NOT NULL,
                FOREIGN KEY (homework_id) REFERENCES homeworks (id) ON DELETE CASCADE
            )
        ''')
        conn.commit()

init_db()

# --- ОБЩИЙ СТИЛЬ (CSS) ДЛЯ ВСЕХ СТРАНИЦ ---
BASE_CSS = """
:root {
    --primary: #4a6fa5;
    --primary-hover: #3b5984;
    --bg: #f4f6f9;
    --surface: #ffffff;
    --text: #333333;
    --border: #cccccc;
    --success: #2ec4b6;
    --danger: #e71d36;
}
* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
body { background: var(--bg); color: var(--text); padding: 20px; display: flex; justify-content: center; }
.container { width: 100%; max-width: 800px; background: var(--surface); padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
h1, h2, h3 { color: var(--primary); margin-bottom: 20px; }
.form-group { margin-bottom: 15px; display: flex; flex-direction: column; }
label { font-weight: 600; margin-bottom: 5px; font-size: 0.95rem; }
input[type="text"], input[type="password"], textarea, file { padding: 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 1rem; width: 100%; }
textarea { resize: vertical; min-height: 120px; }
.btn { display: inline-block; background: var(--primary); color: white; border: none; padding: 12px 20px; border-radius: 6px; font-size: 1rem; cursor: pointer; text-decoration: none; text-align: center; transition: background 0.2s; }
.btn:hover { background: var(--primary-hover); }
.btn-danger { background: var(--danger); }
.btn-danger:hover { background: #b81427; }
.btn-secondary { background: #6c757d; }
.btn-secondary:hover { background: #5a6268; }
.alert { padding: 12px; border-radius: 6px; margin-bottom: 20px; font-weight: bold; }
.alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
.alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
.card { border: 1px solid var(--border); padding: 15px; border-radius: 8px; margin-bottom: 15px; background: #fafafa; }
.flex-between { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; }
table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.95rem; }
th, td { border: 1px solid var(--border); padding: 10px; text-align: left; }
th { background: #f0f2f5; }
.badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; color: white; font-size: 0.85rem; }
.badge-success { background: var(--success); }
.badge-danger { background: var(--danger); }
@media (max-width: 600px) { body { padding: 10px; } .container { padding: 15px; } .flex-between { flex-direction: column; align-items: stretch; } }
"""

# --- ШАБЛОНЫ HTML ---

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Вход в MathCheck</title><style>{{ css|safe }}</style>
</head>
<body>
    <div class="container" style="max-width: 400px; margin-top: 50px;">
        <h1>Вход для репетитора</h1>
        {% with messages = get_flashed_messages(category_filter=["error"]) %}
          {% if messages %}<div class="alert alert-error">{{ messages[0] }}</div>{% endif %}
        {% endwith %}
        <form method="POST">
            <div class="form-group">
                <label>Пароль администратора</label>
                <input type="password" name="password" required autofocus>
            </div>
            <button type="submit" class="btn" style="width:100%;">Войти</button>
        </form>
    </div>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Панель управления MathCheck</title><style>{{ css|safe }}</style>
</head>
<body>
    <div class="container">
        <div class="flex-between">
            <h1>Панель репетитора</h1>
            <a href="{{ url_for('logout') }}" class="btn btn-secondary">Выйти</a>
        </div>
        
        {% with messages = get_flashed_messages(category_filter=["success"]) %}
          {% if messages %}<div class="alert alert-success">{{ messages[0] }}</div>{% endif %}
        {% endwith %}

        <div class="card">
            <h2>Создать новое домашнее задание</h2>
            <form method="POST" action="{{ url_for('create_homework') }}" enctype="multipart/form-data">
                <div class="form-group">
                    <label>Название задания (например: Модули и корни)</label>
                    <input type="text" name="title" required placeholder="Тема урока или дата">
                </div>
                <div class="form-group">
                    <label>Файл задания (PDF)</label>
                    <input type="file" name="pdf_file" accept=".pdf" required>
                </div>
                <div class="form-group">
                    <label>Правильные ответы (по одному в строке, без лишних пробелов)</label>
                    <textarea name="answers" placeholder="Пример:\n5\n-2\n0.5\nх>3" required></textarea>
                </div>
                <button type="submit" class="btn">Создать задание и получить ссылку</button>
            </form>
        </div>

        <h2>Активные задания и результаты</h2>
        {% if not homeworks %}
            <p>Вы еще не создали ни одного задания.</p>
        {% endif %}
        
        {% for hw in homeworks %}
            <div class="card">
                <div class="flex-between" style="border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 10px;">
                    <h3>{{ hw[1] }}</h3>
                    <a href="{{ url_for('delete_homework', hw_id=hw[0]) }}" class="btn btn-danger" onclick="return confirm('Удалить задание и все результаты учеников?')">Удалить ДЗ</a>
                </div>
                <p><strong>Ссылка для ученика:</strong> <input type="text" readonly value="{{ url_for('student_view', hw_id=hw[0], _external=True) }}" onclick="this.select(); text=this.value; navigator.clipboard.writeText(text); alert('Ссылка скопирована!');" style="background: #e9ecef; cursor: pointer; display:inline-block; width: auto; max-width: 100%; font-size:0.9rem; padding: 5px;"></p>
                <p style="margin-top: 5px; font-size: 0.85rem; color: #666;">Создано: {{ hw[4] }} | PDF: <a href="{{ url_for('download_file', filename=hw[2]) }}" target="_blank">Открыть файл</a></p>
                
                <h4 style="margin-top: 15px; color: #555;">Результаты учеников:</h4>
                {% if not results_by_hw[hw[0]] %}
                    <p style="font-size: 0.9rem; color: #888; italic;">Ответов пока нет.</p>
                {% else %}
                    <div style="overflow-x: auto;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Имя ученика</th>
                                    <th>Дата/Время</th>
                                    <th>Ответы ученика</th>
                                    <th>Баллы</th>
                                    <th>Процент</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for res in results_by_hw[hw[0]] %}
                                <tr>
                                    <td><strong>{{ res[2] }}</strong></td>
                                    <td style="font-size:0.8rem; color:#666;">{{ res[7] }}</td>
                                    <td style="font-size:0.85rem; white-space: pre-line;">{{ res[3] }}</td>
                                    <td>{{ res[4] }} из {{ res[5] }}</td>
                                    <td><span class="badge {% if res[6] >= 70 %}badge-success{% else %}badge-danger{% endif %}">{{ "%.0f"|format(res[6]) }}%</span></td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                {% endif %}
            </div>
        {% endfor %}
    </div>
</body>
</html>
"""

STUDENT_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ hw[1] }} - MathCheck</title><style>{{ css|safe }}</style>
</head>
<body>
    <div class="container">
        <h1>Домашнее задание: {{ hw[1] }}</h1>
        
        <div class="card" style="background: #edf2f7; text-align: center; padding: 20px;">
            <p style="margin-bottom: 10px; font-weight: bold;">Шаг 1: Скачайте или откройте файл с условиями задач</p>
            <a href="{{ url_for('download_file', filename=hw[2]) }}" class="btn" target="_blank" style="background:#2b6cb0;">Открыть PDF с заданиями</a>
        </div>

        <form method="POST">
            <div class="card">
                <h2>Шаг 2: Введите ваши данные и ответы</h2>
                <div class="form-group">
                    <label>Ваше Имя и Фамилия</label>
                    <input type="text" name="student_name" placeholder="Например: Иван Иванов" required>
                </div>
                
                <h3 style="margin-top: 20px; font-size: 1.1rem; color: #333;">Внесите ответы на вопросы:</h3>
                <p style="font-size: 0.85rem; color: #666; margin-bottom: 15px;">Внимательно проверяйте знаки, дроби пишите через точку или как указал учитель.</p>
                
                {% for i in range(total_questions) %}
                    <div class="form-group" style="flex-direction: row; align-items: center; margin-bottom: 10px; gap: 10px;">
                        <span style="font-weight: bold; min-width: 30px;">№ {{ i + 1 }}:</span>
                        <input type="text" name="answer_{{ i }}" placeholder="Ваш ответ" required style="max-width: 300px;">
                    </div>
                {% endfor %}
            </div>
            <button type="submit" class="btn" style="width: 100%; font-size: 1.2rem; background: var(--success);">Проверить работу</button>
        </form>
    </div>
</body>
</html>
"""

RESULT_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Результат проверки - MathCheck</title><style>{{ css|safe }}</style>
</head>
<body>
    <div class="container" style="max-width: 500px; text-align: center; margin-top: 30px;">
        <h1>Результат проверки</h1>
        <p style="font-size: 1.2rem; margin-bottom: 20px;">Ученик: <strong>{{ student_name }}</strong></p>
        
        <div class="card" style="padding: 30px; border-radius: 10px;">
            <div style="font-size: 4rem; font-weight: bold; margin-bottom: 10px; color: {% if percentage >= 70 %}var(--success){% else %}var(--danger){% endif %};">
                {{ "%.0f"|format(percentage) }}%
            </div>
            <p style="font-size: 1.3rem; margin-bottom: 10px;">Правильных ответов: <strong>{{ score }}</strong> из <strong>{{ total_questions }}</strong></p>
            <p style="color: #666; font-size: 0.9rem;">Ваши результаты сохранены и отправлены репетитору.</p>
        </div>
        
        <p style="margin-top: 20px; color:#888;">MathCheck © 2026</p>
    </div>
</body>
</html>
"""

# --- МАРШРУТЫ / ЛОГИКА ПРИЛОЖЕНИЯ ---

# Сессия админа (очень простая проверка куки)
def is_admin_authenticated():
    return request.cookies.get('admin_logged_in') == ADMIN_PASSWORD

@app.route('/')
def index():
    if is_admin_authenticated():
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            response = redirect(url_for('admin_dashboard'))
            response.set_cookie('admin_logged_in', ADMIN_PASSWORD)
            return response
        else:
            flash('Неверный пароль администратора!', 'error')
    return render_template_string(LOGIN_HTML, css=BASE_CSS)

@app.route('/logout')
def logout():
    response = redirect(url_for('login'))
    response.delete_cookie('admin_logged_in')
    return response

@app.route('/admin')
def admin_dashboard():
    if not is_admin_authenticated():
        return redirect(url_for('login'))
    
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, pdf_filename, correct_answers, created_at FROM homeworks ORDER BY id DESC")
        homeworks = cursor.fetchall()
        
        results_by_hw = {}
        for hw in homeworks:
            cursor.execute("SELECT id, homework_id, student_name, student_answers, score, total_questions, percentage, submitted_at FROM results WHERE homework_id = ? ORDER BY id DESC", (hw[0],))
            results_by_hw[hw[0]] = cursor.fetchall()
            
    return render_template_string(ADMIN_HTML, css=BASE_CSS, homeworks=homeworks, results_by_hw=results_by_hw)

@app.route('/admin/create', methods=['POST'])
def create_homework():
    if not is_admin_authenticated():
        return redirect(url_for('login'))
        
    title = request.form.get('title')
    answers_raw = request.form.get('answers')
    pdf_file = request.files.get('pdf_file')
    
    if title and answers_raw and pdf_file and pdf_file.filename.endswith('.pdf'):
        # Чистим и форматируем ответы
        answers_list = [line.strip() for line in answers_raw.split('\n') if line.strip()]
        formatted_answers = "\n".join(answers_list)
        
        # Сохраняем файл
        filename = secure_filename(f"{int(datetime.now().timestamp())}_{pdf_file.filename}")
        pdf_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        # Запись в БД
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO homeworks (title, pdf_filename, correct_answers, created_at) VALUES (?, ?, ?, ?)",
                (title, filename, formatted_answers, datetime.now().strftime("%d.%m.%Y %H:%M"))
            )
            conn.commit()
        flash('Домашнее задание успешно создано!', 'success')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/<int:hw_id>')
def delete_homework(hw_id):
    if not is_admin_authenticated():
        return redirect(url_for('login'))
        
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        # Удаляем файл
        cursor.execute("SELECT pdf_filename FROM homeworks WHERE id = ?", (hw_id,))
        row = cursor.fetchone()
        if row:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], row[0]))
            except FileNotFoundError:
                pass
        # Каскадное удаление из БД
        cursor.execute("DELETE FROM homeworks WHERE id = ?", (hw_id,))
        cursor.execute("DELETE FROM results WHERE homework_id = ?", (hw_id,))
        conn.commit()
        
    flash('Задание удалено.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/hw/<int:hw_id>', methods=['GET', 'POST'])
def student_view(hw_id):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, pdf_filename, correct_answers FROM homeworks WHERE id = ?", (hw_id,))
        hw = cursor.fetchone()
        
    if not hw:
        return "Задание не найдено или удалено репетитором.", 404
        
    correct_answers_list = hw[3].split('\n')
    total_questions = len(correct_answers_list)
    
    if request.method == 'POST':
        student_name = request.form.get('student_name', '').strip()
        student_answers = []
        score = 0
        
        # Сбор ответов и подсчет баллов
        student_answers_text_list = []
        for i in range(total_questions):
            ans = request.form.get(f'answer_{i}', '').strip()
            student_answers.append(ans)
            
            # Сравнение без учета регистра
            if ans.lower() == correct_answers_list[i].lower():
                score += 1
                student_answers_text_list.append(f"№{i+1}: {ans} (✅)")
            else:
                student_answers_text_list.append(f"№{i+1}: {ans} (❌, верный: {correct_answers_list[i]})")
                
        percentage = (score / total_questions) * 100 if total_questions > 0 else 0
        student_answers_summary = "\n".join(student_answers_text_list)
        
        # Сохранение результата
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO results (homework_id, student_name, student_answers, score, total_questions, percentage, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (hw_id, student_name, student_answers_summary, score, total_questions, percentage, datetime.now().strftime("%d.%m.%Y %H:%M")))
            conn.commit()
            
        return render_template_string(RESULT_HTML, css=BASE_CSS, student_name=student_name, score=score, total_questions=total_questions, percentage=percentage)

    return render_template_string(STUDENT_HTML, css=BASE_CSS, hw=hw, total_questions=total_questions)

@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # Запуск сервера на всех интерфейсах (чтобы зайти с телефона в той же Wi-Fi сети)
    app.run(host='0.0.0.0', port=5000, debug=True)