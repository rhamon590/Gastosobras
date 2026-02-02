from flask import Flask, render_template, request, redirect, url_for, send_file, session
from database import db
from models import Usuario, Obra, Categoria, NotaFiscal
from sqlalchemy import func
import os
import pandas as pd
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'controle-obras-2026'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///obras.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')

db.init_app(app)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

with app.app_context():
    db.create_all()


    # CRIA USUÁRIO ADMIN (1 VEZ)
    if not Usuario.query.filter_by(usuario='admin').first():
        u = Usuario(nome='Administrador', usuario='admin')
        u.set_senha('1234')
        db.session.add(u)
        db.session.commit()

# ---------------------------------
# FILTRO JINJA — MOEDA BR
# ---------------------------------
def formatar_moeda_brl(valor):
    if valor is None:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

app.jinja_env.filters['moeda_brl'] = formatar_moeda_brl


# ---------------------------------
# FUNÇÃO PARA TRATAR VALOR (BR)
# ---------------------------------
def tratar_valor_brl(valor_raw):
    """
    Aceita:
    R$ 1.234,56
    1.234,56
    1234,56
    1234.56
    """
    valor = (
        valor_raw
        .replace('R$', '')
        .replace(' ', '')
        .replace('.', '')
        .replace(',', '.')
    )
    return float(valor)


# ---------------------------------
# ROTAS
# ---------------------------------
@app.route('/')
def health():
    return "OK", 200

@app.route('/')
def landing():
    return render_template('landing.html')


@app.route('/home')
def home():
    return render_template('home.html')

from models import Usuario

@app.route('/usuarios', methods=['GET', 'POST'])
def usuarios():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nome = request.form['nome']
        usuario = request.form['usuario']
        senha = request.form['senha']

        novo = Usuario(nome=nome, usuario=usuario)
        novo.set_senha(senha)

        db.session.add(novo)
        db.session.commit()

        return redirect(url_for('usuarios'))

    usuarios = Usuario.query.all()
    return render_template('usuarios.html', usuarios=usuarios)


@app.route('/bloquear/<int:id>')
def bloquear_usuario(id):
    u = Usuario.query.get_or_404(id)
    u.ativo = False
    db.session.commit()
    return redirect(url_for('usuarios'))


@app.route('/ativar/<int:id>')
def ativar_usuario(id):
    u = Usuario.query.get_or_404(id)
    u.ativo = True
    db.session.commit()
    return redirect(url_for('usuarios'))

from flask import render_template, request, redirect, url_for, session

from datetime import datetime

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']

        u = Usuario.query.filter_by(usuario=usuario).first()

        if not u or not u.check_senha(senha):
            return render_template('login.html', erro='Usuário ou senha inválidos')

        if not u.ativo:
            return render_template('login.html', erro='Usuário bloqueado')

        session['usuario_id'] = u.id
        session['usuario_nome'] = u.nome

        return redirect(url_for('home'))

    return render_template('login.html')

# ---------------------------------
# DASHBOARD
# ---------------------------------
@app.route('/dashboard')
def dashboard():
    obra_id = request.args.get('obra')
    mes = request.args.get('mes')  # YYYY-MM

    obras = Obra.query.all()

    # -------------------------------
    # QUERY PRINCIPAL (POR CATEGORIA)
    # -------------------------------
    query = (
        db.session.query(
            Categoria.nome,
            func.sum(NotaFiscal.valor)
        )
        .join(NotaFiscal)
    )

    if obra_id and obra_id != "all":
        query = query.filter(NotaFiscal.obra_id == obra_id)

    if mes:
        query = query.filter(NotaFiscal.data.startswith(mes))

    dados = query.group_by(Categoria.nome).all()

    labels = [d[0] for d in dados]
    valores = [float(d[1]) if d[1] else 0 for d in dados]

    total_gasto = sum(valores)
    maior_categoria = max(dados, key=lambda x: x[1])[0] if dados else "—"

    # -------------------------------
    # TOTAL DE NOTAS (COM OU SEM FILTRO)
    # -------------------------------
    query_nfs = NotaFiscal.query

    if obra_id and obra_id != "all":
        query_nfs = query_nfs.filter(NotaFiscal.obra_id == obra_id)

    if mes:
        query_nfs = query_nfs.filter(NotaFiscal.data.startswith(mes))

    total_nfs = query_nfs.count()

    # -------------------------------
    # ÚLTIMA DATA DE LANÇAMENTO
    # -------------------------------
    ultima_nf = query_nfs.order_by(NotaFiscal.data.desc()).first()
    ultima_data = ultima_nf.data if ultima_nf else "—"

    # -------------------------------
    # TOTAL GERAL (TODAS AS OBRAS)
    # -------------------------------
    total_geral_obras = db.session.query(
        func.sum(NotaFiscal.valor)
    ).scalar() or 0

    # -------------------------------
    # RENDER
    # -------------------------------
    return render_template(
        'dashboard.html',
        obras=obras,
        labels=labels,
        valores=valores,
        obra_selecionada=obra_id,
        mes_selecionado=mes,
        total_gasto=total_gasto,
        total_geral_obras=total_geral_obras,  # 👈 NOVO
        maior_categoria=maior_categoria,
        total_nfs=total_nfs,
        ultima_data=ultima_data
    )


# ---------------------------------
# OBRAS
# ---------------------------------
@app.route('/obras', methods=['GET', 'POST'])
def obras():
    if request.method == 'POST':
        db.session.add(Obra(nome=request.form['nome']))
        db.session.commit()
        return redirect(url_for('obras'))

    return render_template('obras.html', obras=Obra.query.all())


@app.route('/obras/editar/<int:id>', methods=['POST'])
def editar_obra(id):
    obra = Obra.query.get_or_404(id)
    obra.nome = request.form['nome']
    db.session.commit()
    return redirect(url_for('obras'))


@app.route('/obras/excluir/<int:id>', methods=['POST'])
def excluir_obra(id):
    obra = Obra.query.get_or_404(id)

    if NotaFiscal.query.filter_by(obra_id=id).first():
        return "Não é possível excluir obra com notas fiscais lançadas", 400

    db.session.delete(obra)
    db.session.commit()
    return redirect(url_for('obras'))


# ---------------------------------
# CATEGORIAS
# ---------------------------------
@app.route('/categorias', methods=['GET', 'POST'])
def categorias():
    if request.method == 'POST':
        db.session.add(Categoria(nome=request.form['nome']))
        db.session.commit()
        return redirect(url_for('categorias'))

    return render_template('categorias.html', categorias=Categoria.query.all())


@app.route('/categorias/editar/<int:id>', methods=['POST'])
def editar_categoria(id):
    categoria = Categoria.query.get_or_404(id)
    categoria.nome = request.form['nome']
    db.session.commit()
    return redirect(url_for('categorias'))


@app.route('/categorias/excluir/<int:id>', methods=['POST'])
def excluir_categoria(id):
    categoria = Categoria.query.get_or_404(id)

    if NotaFiscal.query.filter_by(categoria_id=id).first():
        return "Não é possível excluir categoria vinculada a notas fiscais", 400

    db.session.delete(categoria)
    db.session.commit()
    return redirect(url_for('categorias'))


# ---------------------------------
# NOTAS FISCAIS
# ---------------------------------
@app.route('/nf', methods=['GET', 'POST'])
def nf():
    if request.method == 'POST':

        try:
            valor = tratar_valor_brl(request.form['valor'])
        except ValueError:
            return "Erro: valor inválido. Use ex: 1.234,56", 400

        arquivo = None
        file = request.files.get('arquivo')

        if file and file.filename:
            filename = secure_filename(file.filename)
            caminho = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(caminho)
            arquivo = filename

        nf = NotaFiscal(
            numero=request.form['numero'],
            valor=valor,
            data=request.form['data'],
            pagamento=request.form.get('pagamento'),
            observacao=request.form.get('observacao'),
            obra_id=request.form['obra'],
            categoria_id=request.form['categoria'],
            arquivo=arquivo
        )

        db.session.add(nf)
        db.session.commit()
        return redirect(url_for('nf'))

    return render_template(
        'nf.html',
        obras=Obra.query.all(),
        categorias=Categoria.query.all(),
        nfs=NotaFiscal.query.all()
    )


# ---------------------------------
# DOWNLOAD DE ARQUIVOS
# ---------------------------------
@app.route('/uploads/<filename>')
def abrir_arquivo(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))


# ---------------------------------
# EXPORTAÇÃO
# ---------------------------------
@app.route('/exportar')
def exportar():
    nfs = NotaFiscal.query.all()
    dados = []

    for n in nfs:
        dados.append({
            "Obra": n.obra.nome,
            "Numero NF": n.numero,
            "Categoria": n.categoria.nome,
            "Valor": n.valor,
            "Data": n.data,
            "Pagamento": n.pagamento,
            "Observação": n.observacao
        })

    df = pd.DataFrame(dados)
    path = "relatorio_obras.xlsx"
    df.to_excel(path, index=False)

    return send_file(path, as_attachment=True)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ---------------------------------
# START
# ---------------------------------
if __name__ == "__main__":
    import os
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 3000)),
        debug=True
    )

