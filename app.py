
from flask import Flask, render_template, request, redirect, url_for, session
import firebase_admin
from firebase_admin import credentials, auth, firestore, storage
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Firebase setup
cred = credentials.Certificate("firebase_config.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'expense-tracker-4aa12.appspot.com'
})
db = firestore.client()
bucket = storage.bucket()

# Home page (login/signup)
@app.route('/')
def index():
    return render_template('index.html')

# User Sign-up page
@app.route('/signup')
def signup():
    return render_template('signup.html')

# Handle Sign-up
@app.route('/signup', methods=['POST'])
def signup_post():
    email = request.form['email']
    password = request.form['password']

    try:
        # Create user in Firebase Authentication
        user = auth.create_user(email=email, password=password)
        session['user_id'] = user.uid
        return redirect(url_for('dashboard'))
    except Exception as e:
        return f"Error creating account: {str(e)}"

# User login page
@app.route('/login')
def login_page():
    return render_template('login.html')

# Handle Login
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    try:
        # Firebase Authentication to verify the user
        user = auth.get_user_by_email(email)
        session['user_id'] = user.uid
        return redirect(url_for('dashboard'))
    except Exception as e:
        return f"Error: {str(e)}"

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user_id = session['user_id']
    expenses_ref = db.collection('expenses').where('user_id', '==', user_id)
    expenses = [{**doc.to_dict(), 'id': doc.id} for doc in expenses_ref.stream()]

    return render_template('dashboard.html', expenses=expenses)

@app.route('/add_expense', methods=['POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user_id = session['user_id']
    amount = request.form['amount']
    category = request.form['category']
    description = request.form['description']
    image = request.files['image']

    if image:
        # Upload image to Firebase Storage
        blob = bucket.blob(f'images/{image.filename}')
        blob.upload_from_file(image)

        # Make the file publicly accessible
        blob.make_public()
        image_url = blob.public_url
    else:
        image_url = None

    # Store expense data in Firestore
    db.collection('expenses').add({
        'user_id': user_id,
        'amount': amount,
        'category': category,
        'description': description,
        'image_url': image_url
    })

    return redirect(url_for('dashboard'))

# Edit expense page
@app.route('/edit_expense/<expense_id>')
def edit_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))

    expense_ref = db.collection('expenses').document(expense_id)
    expense = expense_ref.get().to_dict()

    return render_template('edit_expense.html', expense=expense, expense_id=expense_id)

@app.route('/update_expense/<expense_id>', methods=['POST'])
def update_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))

    amount = request.form['amount']
    category = request.form['category']
    description = request.form['description']
    image = request.files['image']

    expense_ref = db.collection('expenses').document(expense_id)

    # Update Firestore document
    updates = {
        'amount': amount,
        'category': category,
        'description': description
    }

    if image:
        # Upload new image to Firebase Storage
        blob = bucket.blob(f'images/{image.filename}')
        blob.upload_from_file(image)

        # Make the file publicly accessible
        blob.make_public()
        updates['image_url'] = blob.public_url

    expense_ref.update(updates)

    return redirect(url_for('dashboard'))

@app.route('/view_file')
def view_file():
    file_url = request.args.get('file_url')

    # Render a template that shows the file
    return render_template('view_file.html', file_url=file_url)


# Handle expense deletion
@app.route('/delete_expense/<expense_id>', methods=['GET'])
def delete_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))

    # Delete from Firestore
    db.collection('expenses').document(expense_id).delete()

    return redirect(url_for('dashboard'))

# Logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)