from flask import render_template, request, redirect, url_for, flash, jsonify, make_response, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime, date, timezone, timedelta
import re
import pandas as pd
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

from app import app
from auth import User
from database import get_db

# Fuso horário do Brasil (UTC-3)
BRASIL_TZ = timezone(timedelta(hours=-3))

def get_brasilia_time():
    """Retorna a hora atual no fuso horário de Brasília"""
    return datetime.now(BRASIL_TZ)

def get_brasilia_date():
    """Retorna a data atual no fuso horário de Brasília"""
    return get_brasilia_time().date()

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.perfil == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('employee_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_input = request.form['login']
        password = request.form['password']
        
        if User.check_password(login_input, password):
            user = User.get_by_login(login_input)
            if user:
                login_user(user)
                
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                
                if user.perfil == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('employee_dashboard'))
            else:
                flash('Erro interno. Tente novamente.', 'danger')
        else:
            flash('Login ou senha incorretos!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.perfil != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('employee_dashboard'))
    
    db = get_db()
    
    # Get today's punch summary
    today = get_brasilia_date().strftime('%d-%m-%Y')
    employees_today = db.execute('''
        SELECT u.nome, u.funcao,
               COUNT(CASE WHEN p.tipo = 'entrada' THEN 1 END) as entrada,
               COUNT(CASE WHEN p.tipo = 'saida_almoco' THEN 1 END) as saida_almoco,
               COUNT(CASE WHEN p.tipo = 'volta_almoco' THEN 1 END) as volta_almoco,
               COUNT(CASE WHEN p.tipo = 'saida_final' THEN 1 END) as saida_final
        FROM usuarios u
        LEFT JOIN pontos p ON u.id = p.usuario_id AND p.data = ?
        WHERE u.perfil = 'colaborador'
        GROUP BY u.id, u.nome, u.funcao
        ORDER BY u.nome
    ''', (today,)).fetchall()
    
    # Get total employees count
    total_employees = db.execute(
        'SELECT COUNT(*) as count FROM usuarios WHERE perfil = "colaborador"'
    ).fetchone()['count']
    
    return render_template('admin_dashboard.html', 
                         employees_today=employees_today,
                         total_employees=total_employees,
                         today=today)

@app.route('/employee')
@login_required
def employee_dashboard():
    if current_user.perfil != 'colaborador':
        return redirect(url_for('admin_dashboard'))
    
    db = get_db()
    today = get_brasilia_date().strftime('%d-%m-%Y')
    
    # Get today's punches for current user
    today_punches = db.execute('''
        SELECT tipo, hora, observacao
        FROM pontos
        WHERE usuario_id = ? AND data = ?
        ORDER BY hora
    ''', (current_user.id, today)).fetchall()
    
    # Determine next punch type
    punch_types = ['entrada', 'saida_almoco', 'volta_almoco', 'saida_final']
    completed_types = [punch['tipo'] for punch in today_punches]
    
    next_punch = None
    for punch_type in punch_types:
        if punch_type not in completed_types:
            next_punch = punch_type
            break
    
    return render_template('employee_dashboard.html',
                         today_punches=today_punches,
                         next_punch=next_punch,
                         today=today)

@app.route('/register_employee', methods=['GET', 'POST'])
@login_required
def register_employee():
    if current_user.perfil != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('employee_dashboard'))
    
    if request.method == 'POST':
        nome = request.form['nome'].strip()
        cpf = request.form['cpf'].strip()
        funcao = request.form['funcao'].strip()
        login = request.form['login'].strip()
        senha = request.form['senha']
        
        # Basic validation
        if not all([nome, cpf, funcao, login, senha]):
            flash('Todos os campos são obrigatórios!', 'danger')
            return render_template('register_employee.html')
        
        # Validate CPF format (basic)
        cpf_clean = re.sub(r'[^0-9]', '', cpf)
        if len(cpf_clean) != 11:
            flash('CPF deve ter 11 dígitos!', 'danger')
            return render_template('register_employee.html')
        
        db = get_db()
        
        # Check if CPF or login already exists
        existing = db.execute(
            'SELECT COUNT(*) as count FROM usuarios WHERE cpf = ? OR login = ?',
            (cpf_clean, login)
        ).fetchone()
        
        if existing['count'] > 0:
            flash('CPF ou login já cadastrado!', 'danger')
            return render_template('register_employee.html')
        
        # Insert new employee
        try:
            db.execute('''
                INSERT INTO usuarios (nome, cpf, funcao, login, senha, perfil)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (nome, cpf_clean, funcao, login, generate_password_hash(senha), 'colaborador'))
            db.commit()
            flash('Colaborador cadastrado com sucesso!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            flash('Erro ao cadastrar colaborador!', 'danger')
            app.logger.error(f'Error registering employee: {e}')
    
    return render_template('register_employee.html')

@app.route('/punch', methods=['POST'])
@login_required
def register_punch():
    if current_user.perfil != 'colaborador':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    observacao = request.form.get('observacao', '').strip()
    
    db = get_db()
    today = get_brasilia_date().strftime('%d-%m-%Y')
    now = get_brasilia_time().strftime('%H:%M:%S')
    
    # Get today's punches for current user
    today_punches = db.execute('''
        SELECT tipo FROM pontos
        WHERE usuario_id = ? AND data = ?
        ORDER BY hora
    ''', (current_user.id, today)).fetchall()
    
    # Determine next punch type
    punch_types = ['entrada', 'saida_almoco', 'volta_almoco', 'saida_final']
    completed_types = [punch['tipo'] for punch in today_punches]
    
    next_punch = None
    for punch_type in punch_types:
        if punch_type not in completed_types:
            next_punch = punch_type
            break
    
    if not next_punch:
        flash('Todos os pontos do dia já foram registrados!', 'warning')
        return redirect(url_for('employee_dashboard'))
    
    # Register punch
    try:
        db.execute('''
            INSERT INTO pontos (usuario_id, data, tipo, hora, observacao)
            VALUES (?, ?, ?, ?, ?)
        ''', (current_user.id, today, next_punch, now, observacao))
        db.commit()
        
        punch_names = {
            'entrada': 'Entrada',
            'saida_almoco': 'Saída para Almoço',
            'volta_almoco': 'Volta do Almoço',
            'saida_final': 'Saída Final'
        }
        
        flash(f'{punch_names[next_punch]} registrada com sucesso às {now}!', 'success')
    except Exception as e:
        flash('Erro ao registrar ponto!', 'danger')
        app.logger.error(f'Error registering punch: {e}')
    
    return redirect(url_for('employee_dashboard'))

@app.route('/punch_history')
@login_required
def punch_history():
    db = get_db()
    
    if current_user.perfil == 'admin':
        # Admin can see all employees
        employee_id = request.args.get('employee_id')
        if employee_id:
            punches = db.execute('''
                SELECT p.data, p.tipo, p.hora, p.observacao, u.nome
                FROM pontos p
                JOIN usuarios u ON p.usuario_id = u.id
                WHERE p.usuario_id = ?
                ORDER BY p.data DESC, p.hora DESC
                LIMIT 100
            ''', (employee_id,)).fetchall()
            
            employee = db.execute(
                'SELECT nome FROM usuarios WHERE id = ?', (employee_id,)
            ).fetchone()
            employee_name = employee['nome'] if employee else 'Funcionário'
        else:
            punches = db.execute('''
                SELECT p.data, p.tipo, p.hora, p.observacao, u.nome
                FROM pontos p
                JOIN usuarios u ON p.usuario_id = u.id
                WHERE u.perfil = 'colaborador'
                ORDER BY p.data DESC, p.hora DESC
                LIMIT 100
            ''').fetchall()
            employee_name = 'Todos os Funcionários'
        
        # Get all employees for dropdown
        employees = db.execute(
            'SELECT id, nome FROM usuarios WHERE perfil = "colaborador" ORDER BY nome'
        ).fetchall()
        
    else:
        # Employee can only see their own punches
        punches = db.execute('''
            SELECT data, tipo, hora, observacao
            FROM pontos
            WHERE usuario_id = ?
            ORDER BY data DESC, hora DESC
            LIMIT 100
        ''', (current_user.id,)).fetchall()
        employee_name = current_user.nome
        employees = []
    
    return render_template('punch_history.html',
                         punches=punches,
                         employee_name=employee_name,
                         employees=employees)

@app.route('/reports')
@login_required
def reports():
    if current_user.perfil != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('employee_dashboard'))
    
    db = get_db()
    
    # Get date range from query parameters
    start_date = request.args.get('start_date', get_brasilia_date().strftime('01-%m-%Y'))
    end_date = request.args.get('end_date', get_brasilia_date().strftime('%d-%m-%Y'))
    employee_id = request.args.get('employee_id')
    
    # Convert dates to YYYY-MM-DD for database queries
    def convert_date_for_db(date_str):
        if date_str and '-' in date_str:
            # Check if format is DD-MM-YYYY
            parts = date_str.split('-')
            if len(parts[0]) == 2:  # DD-MM-YYYY format
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
        return date_str
    
    start_date_db = convert_date_for_db(start_date)
    end_date_db = convert_date_for_db(end_date)
    
    # Get all employees for dropdown
    employees = db.execute(
        'SELECT id, nome FROM usuarios WHERE perfil = "colaborador" ORDER BY nome'
    ).fetchall()
    
    if employee_id:
        # Get detailed report for specific employee
        detailed_punches = db.execute('''
            SELECT p.data, p.tipo, p.hora, p.observacao, u.nome, u.funcao
            FROM pontos p
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE p.usuario_id = ? AND p.data BETWEEN ? AND ?
            ORDER BY p.data, p.hora
        ''', (employee_id, start_date_db, end_date_db)).fetchall()
        
        # Get summary data for the selected employee
        report_data = db.execute('''
            SELECT u.nome, u.funcao,
                   COUNT(DISTINCT CASE WHEN p.tipo = 'entrada' THEN p.data END) as dias_trabalhados,
                   COUNT(DISTINCT p.data) as dias_com_registro,
                   COUNT(p.id) as total_pontos
            FROM usuarios u
            LEFT JOIN pontos p ON u.id = p.usuario_id 
                AND p.data BETWEEN ? AND ?
            WHERE u.id = ?
            GROUP BY u.id, u.nome, u.funcao
        ''', (start_date_db, end_date_db, employee_id)).fetchall()
        
        employee_name = detailed_punches[0]['nome'] if detailed_punches else None
    else:
        # Get general attendance report for all employees
        detailed_punches = []
        report_data = db.execute('''
            SELECT u.nome, u.funcao,
                   COUNT(DISTINCT CASE WHEN p.tipo = 'entrada' THEN p.data END) as dias_trabalhados,
                   COUNT(DISTINCT p.data) as dias_com_registro,
                   COUNT(p.id) as total_pontos
            FROM usuarios u
            LEFT JOIN pontos p ON u.id = p.usuario_id 
                AND p.data BETWEEN ? AND ?
            WHERE u.perfil = 'colaborador'
            GROUP BY u.id, u.nome, u.funcao
            ORDER BY u.nome
        ''', (start_date_db, end_date_db)).fetchall()
        employee_name = None
    
    # Group detailed punches by date for easier template rendering
    punches_by_date = {}
    for punch in detailed_punches:
        date = punch['data']
        if date not in punches_by_date:
            punches_by_date[date] = []
        punches_by_date[date].append(punch)
    
    return render_template('reports.html',
                         report_data=report_data,
                         detailed_punches=detailed_punches,
                         punches_by_date=punches_by_date,
                         employees=employees,
                         employee_id=employee_id,
                         employee_name=employee_name,
                         start_date=start_date,
                         end_date=end_date)

@app.route('/export_history')
@login_required
def export_history():
    if current_user.perfil != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('employee_dashboard'))
    
    format_type = request.args.get('format', 'csv').lower()
    employee_id = request.args.get('employee_id')
    
    db = get_db()
    
    # Query para buscar os dados
    if employee_id:
        punches = db.execute('''
            SELECT p.data, p.tipo, p.hora, p.observacao, u.nome as funcionario
            FROM pontos p
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE p.usuario_id = ?
            ORDER BY p.data DESC, p.hora DESC
        ''', (employee_id,)).fetchall()
        filename_prefix = f"historico_funcionario_{employee_id}"
    else:
        punches = db.execute('''
            SELECT p.data, p.tipo, p.hora, p.observacao, u.nome as funcionario
            FROM pontos p
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE u.perfil = 'colaborador'
            ORDER BY p.data DESC, p.hora DESC
        ''').fetchall()
        filename_prefix = "historico_todos_funcionarios"
    
    if not punches:
        flash('Nenhum dados encontrados para exportar!', 'warning')
        return redirect(url_for('punch_history'))
    
    # Converter para DataFrame
    df = pd.DataFrame([{
        'Data': punch['data'],
        'Funcionário': punch['funcionario'],
        'Tipo de Ponto': {
            'entrada': 'Entrada',
            'saida_almoco': 'Saída Almoço',
            'volta_almoco': 'Volta Almoço',
            'saida_final': 'Saída Final'
        }.get(punch['tipo'], punch['tipo']),
        'Horário': punch['hora'][:5],
        'Observação': punch['observacao'] or '-'
    } for punch in punches])
    
    if format_type == 'csv':
        return export_csv(df, f"{filename_prefix}.csv")
    elif format_type == 'excel':
        return export_excel(df, f"{filename_prefix}.xlsx")
    elif format_type == 'pdf':
        return export_pdf_history(df, f"{filename_prefix}.pdf")
    else:
        flash('Formato de exportação inválido!', 'danger')
        return redirect(url_for('punch_history'))

@app.route('/export_reports')
@login_required
def export_reports():
    if current_user.perfil != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('employee_dashboard'))
    
    format_type = request.args.get('format', 'csv').lower()
    start_date = request.args.get('start_date', get_brasilia_date().strftime('01-%m-%Y'))
    end_date = request.args.get('end_date', get_brasilia_date().strftime('%d-%m-%Y'))
    employee_id = request.args.get('employee_id')
    
    # Convert dates to YYYY-MM-DD for database queries
    def convert_date_for_db(date_str):
        if date_str and '-' in date_str:
            # Check if format is DD-MM-YYYY
            parts = date_str.split('-')
            if len(parts[0]) == 2:  # DD-MM-YYYY format
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
        return date_str
    
    start_date_db = convert_date_for_db(start_date)
    end_date_db = convert_date_for_db(end_date)
    
    db = get_db()
    
    if employee_id:
        # Export detailed report for specific employee
        detailed_punches = db.execute('''
            SELECT p.data, p.tipo, p.hora, p.observacao, u.nome, u.funcao
            FROM pontos p
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE p.usuario_id = ? AND p.data BETWEEN ? AND ?
            ORDER BY p.data, p.hora
        ''', (employee_id, start_date_db, end_date_db)).fetchall()
        
        if not detailed_punches:
            flash('Nenhum dados encontrados para exportar!', 'warning')
            return redirect(url_for('reports'))
        
        employee_name = detailed_punches[0]['nome']
        
        # Group punches by date
        punches_by_date = {}
        for punch in detailed_punches:
            date = punch['data']
            if date not in punches_by_date:
                punches_by_date[date] = []
            punches_by_date[date].append(punch)
        
        filename = f"relatorio_detalhado_{employee_name}_{start_date}_a_{end_date}".replace(' ', '_')
        
        if format_type == 'excel':
            return export_detailed_excel(punches_by_date, filename + ".xlsx", employee_name, start_date, end_date)
        elif format_type == 'pdf':
            return export_detailed_pdf(punches_by_date, filename + ".pdf", employee_name, start_date, end_date)
        else:
            flash('Formato de exportação inválido para relatório detalhado!', 'danger')
            return redirect(url_for('reports'))
    else:
        # Get general attendance report
        report_data = db.execute('''
            SELECT u.nome, u.funcao,
                   COUNT(DISTINCT CASE WHEN p.tipo = 'entrada' THEN p.data END) as dias_trabalhados,
                   COUNT(DISTINCT p.data) as dias_com_registro,
                   COUNT(p.id) as total_pontos
            FROM usuarios u
            LEFT JOIN pontos p ON u.id = p.usuario_id 
                AND p.data BETWEEN ? AND ?
            WHERE u.perfil = 'colaborador'
            GROUP BY u.id, u.nome, u.funcao
            ORDER BY u.nome
        ''', (start_date_db, end_date_db)).fetchall()
        
        if not report_data:
            flash('Nenhum dados encontrados para exportar!', 'warning')
            return redirect(url_for('reports'))
        
        # Converter para DataFrame
        df = pd.DataFrame([{
            'Funcionário': emp['nome'],
            'Função': emp['funcao'],
            'Dias Trabalhados': emp['dias_trabalhados'],
            'Dias com Registro': emp['dias_com_registro'],
            'Total de Pontos': emp['total_pontos'],
            'Frequência (%)': round((emp['dias_trabalhados'] / 30) * 100, 1) if emp['dias_trabalhados'] > 0 else 0
        } for emp in report_data])
        
        filename = f"relatorio_frequencia_{start_date}_a_{end_date}"
        
        if format_type == 'csv':
            return export_csv(df, f"{filename}.csv")
        elif format_type == 'excel':
            return export_excel(df, f"{filename}.xlsx")
        elif format_type == 'pdf':
            return export_pdf_report(df, f"{filename}.pdf", start_date, end_date)
        else:
            flash('Formato de exportação inválido!', 'danger')
            return redirect(url_for('reports'))

def export_csv(df, filename):
    output = io.StringIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    return response

def export_excel(df, filename):
    output = io.BytesIO()
    
    # Usar ExcelWriter corretamente
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    
        # Formatação básica
        workbook = writer.book
        worksheet = writer.sheets['Dados']
        
        # Ajustar largura das colunas
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    
    response = make_response(output.read())
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return response

def export_pdf_history(df, filename):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Título
    title = Paragraph("Histórico de Pontos", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Criar tabela
    data = [df.columns.tolist()]
    data.extend(df.values.tolist())
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.green),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    doc.build(story)
    
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-type"] = "application/pdf"
    return response

def export_pdf_report(df, filename, start_date, end_date):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Título
    title = Paragraph("Relatório de Frequência", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Período
    period = Paragraph(f"Período: {start_date} a {end_date}", styles['Normal'])
    story.append(period)
    story.append(Spacer(1, 12))
    
    # Criar tabela
    data = [df.columns.tolist()]
    data.extend(df.values.tolist())
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.green),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    doc.build(story)
    
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-type"] = "application/pdf"
    return response

def export_detailed_excel(punches_by_date, filename, employee_name, start_date, end_date):
    output = io.BytesIO()
    
    # Create workbook and worksheet  
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Create data for export
        excel_data = []
        for date, punches in sorted(punches_by_date.items()):
            # Convert YYYY-MM-DD to DD-MM-YYYY for display
            date_parts = date.split('-')
            formatted_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
            
            for punch in punches:
                excel_data.append({
                    'Data': formatted_date,
                    'Funcionário': employee_name,
                    'Função': punch['funcao'],
                    'Tipo de Ponto': {
                        'entrada': 'Entrada',
                        'saida_almoco': 'Saída Almoço',
                        'volta_almoco': 'Volta Almoço',
                        'saida_final': 'Saída Final'
                    }.get(punch['tipo'], punch['tipo']),
                    'Horário': punch['hora'][:5],
                    'Observação': punch['observacao'] or ''
                })
        
        df = pd.DataFrame(excel_data)
        df.to_excel(writer, index=False, sheet_name='Relatório Detalhado')
        
        # Format the worksheet
        workbook = writer.book
        worksheet = writer.sheets['Relatório Detalhado']
        
        # Adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    
    response = make_response(output.read())
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return response

def export_detailed_pdf(punches_by_date, filename, employee_name, start_date, end_date):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Título
    title = Paragraph(f"Relatório Detalhado - {employee_name}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Período
    period = Paragraph(f"Período: {start_date} a {end_date}", styles['Normal'])
    story.append(period)
    story.append(Spacer(1, 20))
    
    # Create content for each date
    for date, punches in sorted(punches_by_date.items()):
        # Convert YYYY-MM-DD to DD-MM-YYYY for display
        date_parts = date.split('-')
        formatted_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
        
        # Date header
        date_header = Paragraph(f"<b>{formatted_date}</b>", styles['Heading2'])
        story.append(date_header)
        story.append(Spacer(1, 6))
        
        # Create table for this date
        table_data = [['Tipo de Ponto', 'Horário', 'Observação']]
        
        for punch in punches:
            tipo_nome = {
                'entrada': 'Entrada',
                'saida_almoco': 'Saída Almoço',
                'volta_almoco': 'Volta Almoço',
                'saida_final': 'Saída Final'
            }.get(punch['tipo'], punch['tipo'])
            
            table_data.append([
                tipo_nome,
                punch['hora'][:5],
                punch['observacao'] or '-'
            ])
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 15))
    
    doc.build(story)
    
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-type"] = "application/pdf"
    return response

@app.route('/print_report')
@login_required
def print_report():
    if current_user.perfil != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('employee_dashboard'))
    
    db = get_db()
    
    # Get parameters
    start_date = request.args.get('start_date', get_brasilia_date().strftime('01-%m-%Y'))
    end_date = request.args.get('end_date', get_brasilia_date().strftime('%d-%m-%Y'))
    employee_id = request.args.get('employee_id')
    
    if not employee_id:
        flash('Selecione um funcionário para gerar o relatório de impressão!', 'warning')
        return redirect(url_for('reports'))
    
    # Convert dates to YYYY-MM-DD for database queries
    def convert_date_for_db(date_str):
        if date_str and '-' in date_str:
            # Check if format is DD-MM-YYYY
            parts = date_str.split('-')
            if len(parts[0]) == 2:  # DD-MM-YYYY format
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
        return date_str
    
    start_date_db = convert_date_for_db(start_date)
    end_date_db = convert_date_for_db(end_date)
    
    # Get employee info
    employee = db.execute(
        'SELECT nome, funcao FROM usuarios WHERE id = ?', (employee_id,)
    ).fetchone()
    
    if not employee:
        flash('Funcionário não encontrado!', 'danger')
        return redirect(url_for('reports'))
    
    # Get detailed punches for the employee
    detailed_punches = db.execute('''
        SELECT p.data, p.tipo, p.hora, p.observacao
        FROM pontos p
        WHERE p.usuario_id = ? AND p.data BETWEEN ? AND ?
        ORDER BY p.data, p.hora
    ''', (employee_id, start_date_db, end_date_db)).fetchall()
    
    # Group punches by date
    punches_by_date = {}
    for punch in detailed_punches:
        date = punch['data']
        if date not in punches_by_date:
            punches_by_date[date] = {}
        punches_by_date[date][punch['tipo']] = {
            'hora': punch['hora'][:5],
            'observacao': punch['observacao'] or ''
        }
    
    return render_template('print_report.html',
                         employee=employee,
                         punches_by_date=punches_by_date,
                         start_date=start_date,
                         end_date=end_date)
