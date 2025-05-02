from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS  # Enable CORS for cross-origin requests
from datetime import datetime
import pandas as pd
from flask import send_file
import io

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Enable CORS for all routes with a specific origin (adjust accordingly)



# Create a model for the student with additional fields
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # S.No
    qr_code = db.Column(db.String(50), nullable=False, unique=True)  # QR Code No
    name = db.Column(db.String(100), nullable=False)  # Name
    student_class = db.Column(db.String(50), nullable=False)  # Class
    disrespect_count = db.Column(db.Integer, default=0)  # Disrespect Count
    date_added = db.Column(db.String(50), nullable=False)  # Date
    disrespect_history = db.relationship('DisrespectHistory', backref='student', lazy=True)

    def __repr__(self):
        return f"<Student {self.name}>"

# Disrespect History model to store the timestamp of each disrespect event
class DisrespectHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    count = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.String(50), nullable=False)  # Store date and time

    def __repr__(self):
        return f"<DisrespectHistory StudentID={self.student_id} Count={self.count}>"

# Initialize the database (run this once)
with app.app_context():
    db.create_all()

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, DELETE, PUT, OPTIONS')
    return response

# Route to add a student
@app.route('/add_student', methods=['POST'])
def add_student():
    data = request.json

    # Validate input data
    if not data.get('qr_code') or not data.get('name') or not data.get('class'):
        return jsonify({'message': 'Missing required fields: qr_code, name, or class'}), 400

    qr_code = data.get('qr_code')
    name = data.get('name')
    student_class = data.get('class')
    date_added = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Check if student already exists
    student = Student.query.filter_by(qr_code=qr_code).first()

    if student:
        return jsonify({
            'message': 'Student already exists.',
            'student': {
                'S.No': student.id,
                'QR Code': student.qr_code,
                'Name': student.name,
                'Class': student.student_class,
                'Disrespect Count': student.disrespect_count,
                'Date Added': student.date_added
            }
        }), 400  # Return an error if the student already exists

    # Create a new student if not found
    new_student = Student(
        qr_code=qr_code,
        name=name,
        student_class=student_class,
        disrespect_count=0,  # Initial disrespect count
        date_added=date_added
    )

    db.session.add(new_student)
    db.session.commit()

    return jsonify({
        'message': 'Student added successfully.',
        'student': {
            'S.No': new_student.id,
            'QR Code': new_student.qr_code,
            'Name': new_student.name,
            'Class': new_student.student_class,
            'Disrespect Count': new_student.disrespect_count,
            'Date Added': new_student.date_added
        }
    }), 201

# Route to view all students
@app.route('/view_students', methods=['GET'])
def view_students():
    students = Student.query.all()  # Get all students from the database
    student_data = []
    for student in students:
        student_data.append({
            'S.No': student.id,
            'QR Code': student.qr_code,
            'Name': student.name,
            'Class': student.student_class,
            'Disrespect Count': student.disrespect_count,
            'Date Added': student.date_added,
            'Disrespect History': [{'count': history.count, 'timestamp': history.timestamp} for history in student.disrespect_history]
        })

    return jsonify({'students': student_data})

# Route to register or update a student's disrespect count when QR code is scanned
@app.route('/scan', methods=['POST'])
def scan_qr():
    data = request.json
    qr_code = data.get('qr_code')

    # Validate input data
    if not qr_code:
        return jsonify({'message': 'Missing QR code'}), 400

    # Check if the student exists by qr_code
    student = Student.query.filter_by(qr_code=qr_code).first()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if student:
        # Increment disrespect count if student exists
        student.disrespect_count += 1
        # Create a new disrespect history entry
        new_history = DisrespectHistory(
            student_id=student.id,
            count=student.disrespect_count,
            timestamp=timestamp
        )
        db.session.add(new_history)
        db.session.commit()

        return jsonify({
            'message': 'Student disrespect count updated.',
            'student': {
                'S.No': student.id,
                'QR Code': student.qr_code,
                'Name': student.name,
                'Class': student.student_class,
                'Disrespect Count': student.disrespect_count,
                'Date Added': student.date_added,
                'Disrespect History': [{'count': history.count, 'timestamp': history.timestamp} for history in student.disrespect_history]
            }
        }), 200
    else:
        # Register a new student if not found
        new_student = Student(
            qr_code=qr_code,
            disrespect_count=1,
            date_added=timestamp
        )
        db.session.add(new_student)
        db.session.commit()

        # Create a disrespect history entry for the new student
        new_history = DisrespectHistory(
            student_id=new_student.id,
            count=1,
            timestamp=timestamp
        )
        db.session.add(new_history)
        db.session.commit()

        return jsonify({
            'message': 'New student registered with disrespect count.',
            'student': {
                'S.No': new_student.id,
                'QR Code': new_student.qr_code,
                'Name': new_student.name,
                'Class': new_student.student_class,
                'Disrespect Count': new_student.disrespect_count,
                'Date Added': new_student.date_added,
                'Disrespect History': [{'count': history.count, 'timestamp': history.timestamp} for history in new_student.disrespect_history]
            }
        }), 201
    
# Route to delete a student by QR code
@app.route('/delete_student/<string:qr_code>', methods=['DELETE'])
def delete_student(qr_code):
    try:
        student = Student.query.filter_by(qr_code=qr_code).first()

        if not student:
            return jsonify({'message': 'Student not found'}), 404

        db.session.delete(student)
        db.session.commit()

        return jsonify({'message': f'Student with QR code {qr_code} has been deleted successfully.'}), 200

    except Exception as e:
        import traceback
        traceback.print_exc()  # <-- log full traceback
        return jsonify({'error': str(e)}), 500
    
@app.route('/download_excel', methods=['GET'])
def download_excel():
    students = Student.query.all()

    data = []
    for student in students:
        history_entries = [{'count': h.count, 'timestamp': h.timestamp} for h in student.disrespect_history]
        for history in history_entries:
            data.append({
                'S.No': student.id,
                'QR Code': student.qr_code,
                'Name': student.name,
                'Class': student.student_class,
                'Disrespect Count': history['count'],
                'Date Added': student.date_added,
                'Disrespect Timestamp': history['timestamp']
            })

    # Create DataFrame
    df = pd.DataFrame(data)

    # Create a BytesIO stream and write to Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Students')

    output.seek(0)

    return send_file(
        output,
        download_name="students_data.xlsx",
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )




if __name__ == '__main__':
    app.run(debug=True)
