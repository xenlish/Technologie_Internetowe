from models import db, Member, Book
from app import app

with app.app_context():
    db.create_all()

    if not Member.query.first():
        db.session.add_all([
            Member(name='Alice', email='alice@gmail.com'),
            Member(name='Bob', email='bob@gmail.com')
        ])
    if not Book.query.first():
        db.session.add_all([
            Book(title='Clean Code', author='Robert C. Martin', copies=2),
            Book(title='Python Crash Course', author='Eric Matthes', copies=1)
        ])
    db.session.commit()
    print(" Baza danych została stworzona z przykładowymi danymi.")
