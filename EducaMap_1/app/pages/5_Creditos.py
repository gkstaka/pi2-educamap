import streamlit as st

def render_credits_page():
    st.set_page_config(layout="wide", page_title="Créditos - EducaMap")

    # Injeção de CSS para cartões de equipa
    st.markdown("""
        <style>
        .credits-header {
            text-align: center;
            color: #1F5D8D;
            margin-bottom: 40px;
        }
        .team-container {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 20px;
        }
        .card {
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            padding: 25px;
            width: 250px;
            text-align: center;
            border-top: 5px solid #5fd819;
            transition: transform 0.3s;
        }
        .card:hover {
            transform: translateY(-5px);
        }
        .card h4 {
            color: #1F5D8D;
            margin-bottom: 10px;
        }
        .card p {
            color: #666;
            font-size: 0.9em;
        }
        .footer-note {
            text-align: center;
            margin-top: 50px;
            font-size: 0.8em;
            color: #999;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 class='credits-header'>Equipe de Desenvolvimento</h1>", unsafe_allow_html=True)

    # Organização em colunas para os cartões
    col1, col2, col3, col4 = st.columns(4)

    integrantes = [
        {"nome": "Antônio Alexandre", "funcao": "Estudante IESB"},
        {"nome": "Carlos Eduardo", "funcao": "Estudante IESB"},
        {"nome": "Gustavo Kooiti", "funcao": "Estudante IESB"},
        {"nome": "Lanay Guimarães", "funcao": "Estudante IESB"}
    ]

    cols = [col1, col2, col3, col4]

    for i, person in enumerate(integrantes):
        with cols[i]:
            st.markdown(f"""
                <div class="card">
                    <h4>{person['nome']}</h4>
                    <p>{person['funcao']}</p>
                </div>
            """, unsafe_allow_html=True)

    # Secção de agradecimentos ou referências (opcional)
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; max-width: 800px; margin: 0 auto;'>
            <h3>Agradecimentos</h3>
            <p>O <b>EducaMap</b> foi desenvolvido como um projeto académico focado na melhoria da infraestrutura educacional do Distrito Federal. 
            Agradecemos a todos os colaboradores e às instituições que fornecem dados abertos para o avanço da inteligência geográfica no Brasil.</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='footer-note'>EducaMap © 2026 - Versão 1.0</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    render_credits_page()
