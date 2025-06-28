from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///claims.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Claim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.String(50), nullable=False)
    patient_name = db.Column(db.String(100), nullable=False)
    doa = db.Column(db.String(20), nullable=False)
    dod = db.Column(db.String(20), nullable=False)
    claim_amount = db.Column(db.Float, nullable=False)
    deadline = db.Column(db.String(50), nullable=False)  # ISO format

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    claims = Claim.query.order_by(Claim.id).all()
    return render_template('index.html', claims=claims)

@app.route('/add', methods=['POST'])
def add_claim():
    claim_id = request.form['claim_id']
    patient_name = request.form['patient_name']
    doa = request.form['doa']
    dod = request.form['dod']
    claim_amount = float(request.form['claim_amount'])
    dod_date = datetime.strptime(dod, '%Y-%m-%d')
    deadline = dod_date + timedelta(days=7)

    new_claim = Claim(
        claim_id=claim_id,
        patient_name=patient_name,
        doa=doa,
        dod=dod,
        claim_amount=claim_amount,
        deadline=deadline.isoformat()
    )
    db.session.add(new_claim)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete_claim(id):
    claim = Claim.query.get_or_404(id)
    db.session.delete(claim)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_claim(id):
    claim = Claim.query.get_or_404(id)
    if request.method == 'POST':
        claim.claim_id = request.form['claim_id']
        claim.patient_name = request.form['patient_name']
        claim.doa = request.form['doa']
        claim.dod = request.form['dod']
        claim.claim_amount = float(request.form['claim_amount'])
        dod_date = datetime.strptime(claim.dod, '%Y-%m-%d')
        deadline = dod_date + timedelta(days=7)
        claim.deadline = deadline.isoformat()

        db.session.commit()
        return redirect(url_for('index'))

    return render_template('edit.html', claim=claim)

@app.route('/export/excel')
def export_excel():
    claims = Claim.query.all()
    data = []
    for c in claims:
        data.append({
            'Claim ID': c.claim_id,
            'Patient Name': c.patient_name,
            'DOA': c.doa,
            'DOD': c.dod,
            'Claim Amount': c.claim_amount,
            'Deadline': c.deadline
        })
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Claims')
    output.seek(0)
    return send_file(output, download_name="claims.xlsx", as_attachment=True)

@app.route('/export/pdf')
def export_pdf():
    claims = Claim.query.all()
    output = BytesIO()
    p = canvas.Canvas(output, pagesize=letter)
    width, height = letter
    y = height - 40
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, "Claim Tracker Report")
    p.setFont("Helvetica", 10)
    y -= 30
    for c in claims:
        line = f"ID: {c.claim_id}, Patient: {c.patient_name}, DOA: {c.doa}, DOD: {c.dod}, Amount: {c.claim_amount}"
        p.drawString(40, y, line)
        y -= 15
        if y < 40:
            p.showPage()
            y = height - 40
    p.save()
    output.seek(0)
    return send_file(output, download_name="claims.pdf", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
