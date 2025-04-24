# app.py
import streamlit as st
import pandas as pd
import os
import re
import tempfile
import OpenAI

# Nastavení stránky
st.set_page_config(
    page_title="EDUasistent - Hodnocení textů",
    page_icon="📝",
    layout="wide"
)

# Nadpis a úvod
st.title("📝 EDUasistent - Hodnocení textů")
st.markdown("""
    Aplikace pro automatické porovnání a hodnocení textů žáků vůči vzorovému textu pomocí AI.
    
    Nahrajte vzorový text a práce žáků pro získání zpětné vazby.
""")

# Inicializace session state pro uchování dat mezi refreshi stránky
if 'openai_api_key' not in st.session_state:
    st.session_state.openai_api_key = ""
if 'results' not in st.session_state:
    st.session_state.results = []
if 'temp_dir' not in st.session_state:
    st.session_state.temp_dir = tempfile.mkdtemp()

# Sidebar pro nastavení
with st.sidebar:
    st.header("Nastavení")
    
    api_key = st.text_input("OpenAI API klíč:", 
                           value=st.session_state.openai_api_key,
                           type="password",
                           help="Zadejte váš OpenAI API klíč")
    
    if api_key != st.session_state.openai_api_key:
        st.session_state.openai_api_key = api_key
    
    st.markdown("---")
    
    model = st.selectbox(
        "Model AI:",
        ["gpt-3.5-turbo", "gpt-4"],
        index=0,
        help="Vyberte AI model pro analýzu textů"
    )
    
    temperature = st.slider(
        "Kreativita modelu:",
        min_value=0.0,
        max_value=1.0,
        value=0.3,
        step=0.1,
        help="Nižší hodnota = konzistentnější odpovědi, vyšší hodnota = kreativnější odpovědi"
    )
    
    st.markdown("---")
    
    export_format = st.selectbox(
        "Formát exportu výsledků:",
        ["CSV", "Excel"],
        index=0
    )
    
    st.markdown("---")
    
    st.info("Vytvořeno na základě původního Jupyter notebooku EDUasistent.")

# Funkce pro analýzu textu
def analyze_text(reference_text, student_text, api_key, model, temperature):
    prompt = f"""
Porovnej následující text žáka s ideálním vzorovým textem. Uveď:

1. Hlavní rozdíly, chyby nebo nedostatky.
2. Doporučení k vylepšení.
3. Odhadni celkové hodnocení na stupnici 1 (nejhorší) až 5 (výborné).

--- VZOR ---
{reference_text}

--- ŽÁK ---
{student_text}

Odpověď formuluj česky, přehledně.
"""
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Chyba: {str(e)}"

# Hlavní část aplikace
col1, col2 = st.columns(2)

with col1:
    st.header("Nahrání souborů")
    
    # Nahrání vzorového textu
    st.subheader("1. Nahrajte vzorový text")
    reference_file = st.file_uploader("Vzorový text (*.txt)", type="txt", key="reference")
    
    if reference_file:
        try:
            reference_text = reference_file.getvalue().decode("utf-8")
            with st.expander("Náhled vzorového textu"):
                st.text_area("Vzorový text:", reference_text, height=200, disabled=True)
        except UnicodeDecodeError:
            try:
                reference_text = reference_file.getvalue().decode("windows-1250")
                with st.expander("Náhled vzorového textu"):
                    st.text_area("Vzorový text:", reference_text, height=200, disabled=True)
            except:
                st.error("Nepodařilo se načíst vzorový text. Zkontrolujte kódování souboru.")
                reference_text = None
    else:
        reference_text = None
    
    # Nahrání prací žáků
    st.subheader("2. Nahrajte texty žáků")
    student_files = st.file_uploader("Práce žáků (*.txt)", type="txt", accept_multiple_files=True, key="students")
    
    if student_files:
        st.success(f"Nahráno {len(student_files)} souborů.")
    
    # Tlačítko pro analýzu
    st.subheader("3. Spusťte analýzu")
    analyze_button = st.button("🔍 Analyzovat texty", type="primary", disabled=(not reference_text or not student_files or not st.session_state.openai_api_key))
    
    if analyze_button and reference_text and student_files and st.session_state.openai_api_key:
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, file in enumerate(student_files):
            status_text.text(f"Analyzuji soubor {i+1}/{len(student_files)}: {file.name}")
            try:
                try:
                    student_text = file.getvalue().decode("utf-8")
                except UnicodeDecodeError:
                    student_text = file.getvalue().decode("windows-1250")
                
                feedback = analyze_text(reference_text, student_text, st.session_state.openai_api_key, model, temperature)
                
                # Extrahujeme hodnocení z feedbacku
                score_match = re.search(r"(?i)(hodnocení.*?([1-5]))", feedback)
                score = score_match.group(2) if score_match else "?"
                
                results.append({
                    "soubor": file.name,
                    "hodnocení (1–5)": score,
                    "zpětná vazba": feedback
                })
                
            except Exception as e:
                results.append({
                    "soubor": file.name,
                    "hodnocení (1–5)": "X",
                    "zpětná vazba": f"Chyba při zpracování: {str(e)}"
                })
            
            progress_bar.progress((i + 1) / len(student_files))
        
        status_text.text("Analýza dokončena!")
        st.session_state.results = results

with col2:
    st.header("Výsledky hodnocení")
    
    if st.session_state.results:
        # Výsledky v tabulce
        df = pd.DataFrame(st.session_state.results)
        st.dataframe(df[["soubor", "hodnocení (1–5)"]], use_container_width=True)
        
        # Možnost stažení výsledků
        if export_format == "CSV":
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Stáhnout výsledky (CSV)",
                data=csv,
                file_name="eduasistent_vysledky.csv",
                mime="text/csv",
            )
        else:
            excel_buffer = pd.ExcelWriter("eduasistent_vysledky.xlsx", engine='xlsxwriter')
            df.to_excel(excel_buffer, index=False)
            excel_buffer.close()
            with open("eduasistent_vysledky.xlsx", "rb") as f:
                excel_data = f.read()
            st.download_button(
                label="⬇️ Stáhnout výsledky (Excel)",
                data=excel_data,
                file_name="eduasistent_vysledky.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        # Detail zpětné vazby
        st.subheader("Detail zpětné vazby")
        if st.session_state.results:
            selected_file = st.selectbox(
                "Vyberte soubor pro zobrazení detailu:",
                [result["soubor"] for result in st.session_state.results]
            )
            
            selected_result = next((item for item in st.session_state.results if item["soubor"] == selected_file), None)
            
            if selected_result:
                st.markdown(f"**Hodnocení:** {selected_result['hodnocení (1–5)']}/5")
                st.markdown("**Zpětná vazba:**")
                st.markdown(selected_result["zpětná vazba"])
    else:
        st.info("Zde se zobrazí výsledky po nahrání souborů a spuštění analýzy.")

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center">
        <p>© 2025 EDUasistent | Automatické hodnocení textů pomocí AI</p>
    </div>
""", unsafe_allow_html=True)
