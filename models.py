from database import db
from werkzeug.security import generate_password_hash, check_password_hash


class Obra(db.Model):
    __tablename__ = 'obra'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<Obra {self.nome}>"


class Categoria(db.Model):
    __tablename__ = 'categoria'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f"<Categoria {self.nome}>"


class NotaFiscal(db.Model):
    __tablename__ = 'nota_fiscal'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.String(20), nullable=False)
    pagamento = db.Column(db.String(50))
    observacao = db.Column(db.String(200))
    arquivo = db.Column(db.String(200))

    obra_id = db.Column(db.Integer, db.ForeignKey('obra.id'), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)

    obra = db.relationship('Obra', backref=db.backref('notas_fiscais', lazy=True))
    categoria = db.relationship('Categoria', backref=db.backref('notas_fiscais', lazy=True))

    def __repr__(self):
        return f"<NotaFiscal {self.numero}>"


class Usuario(db.Model):
    __tablename__ = 'usuario'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, default=True)

    def set_senha(self, senha):
        self.senha = generate_password_hash(senha)

    def check_senha(self, senha):
        return check_password_hash(self.senha, senha)
