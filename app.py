from celery import Celery
from flask import Flask, render_template, request, url_for, redirect
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:root123@localhost:3306/message'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

db = SQLAlchemy(app)

def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL'],
        backend=app.config['CELERY_RESULT_BACKEND']
    )
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery

celery = make_celery(app)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    subject = db.Column(db.String(100))
    message = db.Column(db.Text)

    def __repr__(self):
        return f'<Message {self.id} - {self.name} - {self.subject}>'


@app.route('/submit_sync_message', methods=['POST'])
def submit_sync_message():
    name = request.form['name']
    subject = request.form['subject']
    message = request.form['message']
    # Zapisanie danych do bazy danych
    new_message = Message(name=name, subject=subject, message=message)
    db.session.add(new_message)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/submit_async_message', methods=['POST'])
def submit_async_message():
    try:
        name = request.form['name']
        subject = request.form['subject']
        message = request.form['message']

        print(f"Received async message: name={name}, subject={subject}, message={message}")  # Logging received data

        save_message.delay(name, subject, message)
        return "Message submitted successfully", 200
    except Exception as e:
        print(f"Error: {e}")  # Logging error
        return "There was an issue with your submission", 500


@celery.task
def save_message(name, subject, message):
    new_message = Message(name=name, subject=subject, message=message)
    db.session.add(new_message)
    db.session.commit()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/sync_form')
def show_sync_form():
    return render_template('sync_form.html')


@app.route('/async_form')
def show_async_form():
    return render_template('async_form.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
