from flask import Flask, jsonify, request
from datetime import date, timedelta
from models import db, Member, Book, Loan
from flask import send_from_directory

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return send_from_directory('static', 'index.html')

# ----- KLIENCI -----
@app.route('/api/members', methods=['GET'])
def get_members():
    members = Member.query.all()
    return jsonify([{'id': m.id, 'name': m.name, 'email': m.email} for m in members])

@app.route('/api/members', methods=['POST'])
def add_member():
    data = request.get_json()
    if not data or 'name' not in data or 'email' not in data:
        return jsonify({'błąd': 'Nie dodano imienia lub adresu email'}), 400

    if Member.query.filter_by(email=data['email']).first():
        return jsonify({'bład': 'Ten adres email już istnieje'}), 409

    member = Member(name=data['name'], email=data['email'])
    db.session.add(member)
    db.session.commit()
    return jsonify({'id': member.id}), 201

# ----- KSIĄZKI -----
@app.route('/api/books', methods=['GET'])
def get_books():
    books = Book.query.all()
    result = []
    for b in books:
        active_loans = Loan.query.filter_by(book_id=b.id, return_date=None).count()
        available = max(b.copies - active_loans, 0)
        result.append({
            'id': b.id,
            'title': b.title,
            'author': b.author,
            'copies': b.copies,
            'available': available
        })
    return jsonify(result)

@app.route('/api/books', methods=['POST'])
def add_book():
    data = request.get_json()
    if not data or 'title' not in data or 'author' not in data:
        return jsonify({'błąd': 'Nie znaleziona autora lub tytułu.'}), 400

    copies = data.get('copies', 1)
    book = Book(title=data['title'], author=data['author'], copies=copies)
    db.session.add(book)
    db.session.commit()
    return jsonify({'id': book.id}), 201

@app.route('/api/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    book = Book.query.get(book_id)
    if not book:
        return jsonify({'błąd': f'książka z id={book_id} nie została znaleziona'}), 404

    active_loans = Loan.query.filter_by(book_id=book.id, return_date=None).count()
    if active_loans > 0:
        return jsonify({'bład': 'Nie można usunąć, książka jest wypożyczona!'}), 409

    db.session.delete(book)
    db.session.commit()
    return jsonify({'Wiadomość': 'Książka została usunięta'}), 200


# ----- WYPOŻYCZENIA -----
@app.route('/api/loans', methods=['GET'])
def get_loans():
    loans = Loan.query.all()
    return jsonify([{
        'id': l.id,
        'member_id': l.member_id,
        'book_id': l.book_id,
        'loan_date': l.loan_date.isoformat(),
        'due_date': l.due_date.isoformat(),
        'return_date': l.return_date.isoformat() if l.return_date else None
    } for l in loans])

@app.route('/api/loans/borrow', methods=['POST'])
def borrow_book():
    data = request.get_json()
    member = Member.query.get(data.get('member_id'))
    book = Book.query.get(data.get('book_id'))
    if not member or not book:
        return jsonify({'error': 'Książka lub Klient nie został znaleziony'}), 404

    active_loans = Loan.query.filter_by(book_id=book.id, return_date=None).count()
    if active_loans >= book.copies:
        return jsonify({'błąd': 'Nie ma już kopii'}), 409

    loan = Loan(member_id=member.id, book_id=book.id,
                loan_date=date.today(),
                due_date=date.today() + timedelta(days=14))
    db.session.add(loan)
    db.session.commit()
    return jsonify({'loan_id': loan.id}), 201

@app.route('/api/loans/return', methods=['POST'])
def return_book():
    data = request.get_json()
    loan = Loan.query.get(data.get('loan_id'))
    if not loan:
        return jsonify({'Błąd': 'Nie znaleziono wypożyczenia'}), 404
    if loan.return_date:
        return jsonify({'błąd': 'Książka została już zwrócona'}), 409

    loan.return_date = date.today()
    db.session.commit()
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(debug=True)
