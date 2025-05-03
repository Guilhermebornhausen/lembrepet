# MVP do LembrePet - Cadastro de Clientes, Pets e Lembretes
import streamlit as st
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import smtplib
from email.message import EmailMessage
import json
import tempfile

# Inicializar Firebase a partir de secrets (sem caminho físico)
if 'firebase_initialized' not in st.session_state:
    firebase_json = st.secrets["FIREBASE_CREDENTIALS_JSON"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmpfile:
        tmpfile.write(firebase_json.encode())
        cred = credentials.Certificate(tmpfile.name)
        firebase_admin.initialize_app(cred)
    st.session_state['firebase_initialized'] = True

db = firestore.client()

st.set_page_config(page_title="LembrePet", layout="centered")
st.title("📋 Cadastro de Pet e Lembrete")

st.header("1. Informações do Dono")
nome_dono = st.text_input("Nome do Responsável")
email_dono = st.text_input("E-mail do Responsável")
telefone = st.text_input("Telefone (WhatsApp)")

st.header("2. Informações do Pet")
nome_pet = st.text_input("Nome do Pet")
tipo_pet = st.selectbox("Tipo", ["Cachorro", "Gato", "Outro"])
data_nasc = st.date_input("Data de nascimento")

st.header("3. Lembrete")
tipo_lembrete = st.selectbox("Tipo de lembrete", ["Vacina", "Vermífugo", "Banho/Tosa", "Consulta"])
data_lembrete = st.date_input("Data do lembrete", min_value=datetime.date.today())
hora_lembrete = st.time_input("Horário do lembrete")

if st.button("Salvar Cadastro"):
    doc = {
        "nome_dono": nome_dono,
        "email_dono": email_dono,
        "telefone": telefone,
        "nome_pet": nome_pet,
        "tipo_pet": tipo_pet,
        "data_nasc": str(data_nasc),
        "tipo_lembrete": tipo_lembrete,
        "data_lembrete": str(data_lembrete),
        "hora_lembrete": str(hora_lembrete),
        "created_at": datetime.datetime.now()
    }
    db.collection("lembretes").add(doc)
    st.success("Cadastro salvo com sucesso! 🐾")

st.markdown("---")
st.header("📅 Lembretes Agendados")

filtro_data = st.date_input("Filtrar por data específica", value=datetime.date.today())
filtro_tipo = st.selectbox("Filtrar por tipo de lembrete", ["Todos", "Vacina", "Vermífugo", "Banho/Tosa", "Consulta"])

lembretes_ref = db.collection("lembretes").where("data_lembrete", "==", str(filtro_data)).order_by("hora_lembrete")
lembretes = lembretes_ref.stream()

lista_lembretes = []
for lembrete in lembretes:
    doc_id = lembrete.id
    data = lembrete.to_dict()
    if filtro_tipo == "Todos" or data["tipo_lembrete"] == filtro_tipo:
        st.write(f"🐾 **{data['nome_pet']}** ({data['tipo_pet']}) - {data['tipo_lembrete']} em {data['data_lembrete']} às {data['hora_lembrete']}")
        st.caption(f"Responsável: {data['nome_dono']} - {data['telefone']}")

        if st.button(f"Excluir {data['nome_pet']} - {data['tipo_lembrete']} ({doc_id})"):
            if st.confirm("Tem certeza que deseja excluir este lembrete?"):
                db.collection("lembretes").document(doc_id).delete()
                st.success(f"Lembrete de {data['nome_pet']} excluído!")
                st.experimental_rerun()

        lista_lembretes.append({
            "Pet": data['nome_pet'],
            "Tipo": data['tipo_pet'],
            "Lembrete": data['tipo_lembrete'],
            "Data": data['data_lembrete'],
            "Hora": data['hora_lembrete'],
            "Responsável": data['nome_dono'],
            "Telefone": data['telefone'],
            "Email": data['email_dono']
        })

if lista_lembretes:
    df = pd.DataFrame(lista_lembretes)
    st.download_button("📄 Exportar lembretes como Excel", data=df.to_csv(index=False).encode('utf-8'), file_name="lembretes.csv", mime="text/csv")

    if st.button("✉️ Enviar e-mails de lembrete"):
        EMAIL = st.secrets["email"]
        SENHA = st.secrets["senha"]
        for item in lista_lembretes:
            msg = EmailMessage()
            msg['Subject'] = f"Lembrete: {item['Lembrete']} para {item['Pet']}"
            msg['From'] = EMAIL
            msg['To'] = item['Email']
            msg.set_content(
                f"Olá {item['Responsável']},

"
                f"Este é um lembrete de que o(a) {item['Pet']} tem um compromisso de {item['Lembrete']} "
                f"agendado para {item['Data']} às {item['Hora']}.

"
                "Atenciosamente,
Equipe LembrePet"
            )

            try:
                with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
                    smtp.starttls()
                    smtp.login(EMAIL, SENHA)
                    smtp.send_message(msg)
                st.success(f"E-mail enviado para {item['Email']}")
            except Exception as e:
                st.error(f"Erro ao enviar para {item['Email']}: {e}")