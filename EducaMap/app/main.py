"""
Página principal do Sistema EducaMap.
Apresentação do projeto e portal de navegação padronizado.
"""

import streamlit as st
from app.modules.data_utils import load_data_from_postgres

def main() -> None:
    # 1. Configuração da Página e Estado Inicial
    st.set_page_config(
        layout="wide", 
        page_title="EducaMap - Apresentação",
        initial_sidebar_state="expanded"
    )

    # 2. Injeção de CSS para Padronização de Layout
    st.markdown("""
        <style>
        /* Remove o botão hambúrguer (impede fechar a barra lateral) */
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        
        /* Remove o cabeçalho e rodapé nativos */
        header {visibility: hidden;}
        footer {visibility: hidden;}

        /* Estilização da Barra Lateral */
        [data-testid="stSidebar"] {
            min-width: 280px !important;
            max-width: 280px !important;
            /* background-color: #f8f9fa; */
        }

        /* Estilização dos elementos de apresentação */
        .main-header {
            background-color: #1F5D8D;
            padding: 30px;
            border-radius: 10px;
            color: white;
            text-align: center;
            margin-bottom: 20px;
        }
        .info-box {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 10px;
            color: #333;
            border-left: 5px solid #1F5D8D;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin-top: 15px;
        }
        .ods-tag {
            background-color: #5fd819;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

    # 3. Carregamento de Dados para validação
    try:
        df = load_data_from_postgres()
        total_escolas = len(df)
    except Exception as exc:
        st.sidebar.error(f"Erro de conexão: {exc}")
        total_escolas = 0

    # --- BARRA LATERAL PADRONIZADA ---
    with st.sidebar:
        # Título em azul marinho
        st.markdown("<h1 style='color: #1F5D8D; margin-bottom: 0;'>EducaMap</h1>", unsafe_allow_html=True)
        # Nome da página atual
        st.markdown("<p style='color: #666; font-size: 1.1rem; font-weight: bold;'>Apresentação</p>", unsafe_allow_html=True)
        
        st.divider() # Barra de separação
        
        # Filtros (Não aplicáveis na home, mas mantendo o espaço conforme padrão)
        st.info("Selecione uma ferramenta no menu acima para aplicar filtros.")

        st.divider() # Barra de separação
        
        # Instruções Gerais
        st.markdown("**Instruções**")
        st.caption("Bem-vindo ao EducaMap. Utilize os módulos ao lado para analisar a infraestrutura escolar do DF.")

    # --- CONTEÚDO PRINCIPAL ---
    st.markdown("""
        <div class="main-header">
            <h1>EducaMap</h1>
            <p>Inteligência Geográfica Aplicada ao Planejamento Educacional do Distrito Federal.</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
            <div class="info-box">
                <h3>Sobre o Projeto</h3>
                <p>O <b>EducaMap</b> identifica "desertos educacionais" no território do Distrito Federal, cruzando dados georreferenciados do INEP para apoiar gestores públicos.</p>
                <p>Nossa solução utiliza mapas de calor e cálculos de raio de abrangência para visualizar onde a oferta escolar precisa de atenção prioritária.</p>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<span class="ods-tag">Conexão ODS 4</span>', unsafe_allow_html=True)
        st.write("")
        st.write("**Meta 4.a:** Melhorar instalações físicas para educação que sejam apropriadas para crianças e inclusivas.")
        
        if total_escolas > 0:
            st.metric("Escolas Georreferenciadas", total_escolas)

    st.divider()
    st.subheader("Funcionalidades Principais")
    
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        st.write("📍 **Mapa de Raios**")
        st.caption("Visualização da área de atendimento baseada no porte da escola.")
    with fcol2:
        st.write("🔥 **Mapa de Calor**")
        st.caption("Densidade de matrículas e identificação de polos de demanda.")
    with fcol3:
        st.write("📊 **Análise de Dados**")
        st.caption("Gráficos interativos e tabelas detalhadas para exportação.")

if __name__ == "__main__":
    main()
