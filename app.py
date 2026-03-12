import json
import os
import streamlit as st
import pandas as pd
import yfinance as yf

# Mini-baza wartości aktualnych (miesięczne kwoty: spółka, prywatnie)
DATA_DIR = "data"
ACTUALS_FILE = os.path.join(DATA_DIR, "actuals.json")


def load_actuals() -> dict:
    """Ładuje zapisane wartości aktualne z JSON. Klucze: YYYY-MM, wartości: {spolka, prywatnie}."""
    if not os.path.isfile(ACTUALS_FILE):
        return {}
    try:
        with open(ACTUALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_actuals(data: dict) -> None:
    """Zapisuje wartości aktualne do JSON."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(ACTUALS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="FIRE Dashboard 2026", layout="wide")

st.title("🚀 Strategia FIRE 2026: Mode POWOŁANIE (Art. 201 KSH)")
st.markdown(
    "Symulator: Spółka z o.o. (CIT 9%) + Powołanie (PIT + Zdrowotna 9%) + Złoto")

# --- POMOCNICZE / API ---


@st.cache_data(ttl=3600)
def get_gold_price_pln() -> tuple[float, float]:
    try:
        gold = yf.Ticker("GC=F")
        gold_price_usd = gold.history(period="1d")["Close"].iloc[-1]
        forex = yf.Ticker("USDPLN=X")
        usd_pln_rate = forex.history(period="1d")["Close"].iloc[-1]
        return float(gold_price_usd * usd_pln_rate), float(usd_pln_rate)
    except Exception as e:
        st.error(f"Błąd API: {e}")
        return 20000.0, 4.0


@st.cache_data(ttl=3600)
def get_silver_price_pln() -> float:
    """Aktualna cena uncji srebra w PLN (SI=F * USDPLN)."""
    try:
        silver = yf.Ticker("SI=F")
        silver_price_usd = silver.history(period="1d")["Close"].iloc[-1]
        forex = yf.Ticker("USDPLN=X")
        usd_pln_rate = forex.history(period="1d")["Close"].iloc[-1]
        return float(silver_price_usd * usd_pln_rate)
    except Exception as e:
        st.error(f"Błąd API (srebro): {e}")
        return 100.0


@st.cache_data(ttl=3600)
def get_metals_history_df() -> pd.DataFrame:
    """Historia cen złota i srebra w PLN (ostatni rok, dziennie)."""
    try:
        data = yf.download(
            ["GC=F", "SI=F", "USDPLN=X"], period="1y", interval="1d"
        )["Close"].dropna()
        gold_pln = data["GC=F"] * data["USDPLN=X"]
        silver_pln = data["SI=F"] * data["USDPLN=X"]
        df = pd.DataFrame(
            {
                "Złoto (PLN/oz)": gold_pln,
                "Srebro (PLN/oz)": silver_pln,
            }
        )
        df.index = df.index.date
        return df
    except Exception as e:
        st.error(f"Błąd pobierania historii metali: {e}")
        return pd.DataFrame()

def calculate_net_appointment(monthly_brutto):
    """
    Logika Powołania 2026:
    - Składka zdrowotna: 9% od pełnego wynagrodzenia (płacona zawsze).
    - Kwota wolna od PIT: 30 000 PLN rocznie – do tej kwoty PIT nie jest płacony.
    - PIT: 12% (do 120k rocznie) / 32% (nadwyżka), od podstawy pomniejszonej o 30 000 rocznie.
    """
    annual_brutto = monthly_brutto * 12
    health_ins = monthly_brutto * 0.09

    if annual_brutto <= 120000:
        # Podatek = (Podstawa - Kwota Wolna) * 12%
        annual_tax = max(0, (annual_brutto - 30000) * 0.12)
    else:
        tax_low = (120000 - 30000) * 0.12
        tax_high = (annual_brutto - 120000) * 0.32
        annual_tax = tax_low + tax_high

    monthly_tax = annual_tax / 12
    netto = monthly_brutto - health_ins - monthly_tax
    return netto, health_ins, monthly_tax


# --- SIDEBAR - PARAMETRY ---
st.sidebar.header("⚙️ Parametry Wejściowe")

invoice_amount_gross = st.sidebar.number_input(
    "Faktura Miesięczna Spółki (Brutto PLN)", min_value=0, value=27000, step=1000
)
invoice_amount = st.sidebar.number_input(
    "Faktura Miesięczna Spółki (Netto PLN)", min_value=0, value=20000, step=1000
)

st.sidebar.subheader("🧾 Podsumowanie faktury")
# wg Twojego założenia: z brutto bierzemy ~77% jako „netto” (czyli brutto * 0.77)
invoice_net_from_gross = invoice_amount_gross * 0.77
invoice_net_total = invoice_amount + invoice_net_from_gross

col_inv1, col_inv2 = st.sidebar.columns(2)
with col_inv1:
    st.metric("Suma brutto", f"{invoice_amount_gross:,.0f} PLN")
with col_inv2:
    st.metric("Suma netto (pole)", f"{invoice_amount:,.0f} PLN")

# st.sidebar.write(f"Netto z brutto (brutto × 0.77): **{invoice_net_from_gross:,.0f} PLN**")
st.sidebar.success(f"Netto razem: **{invoice_net_total:,.0f} PLN**")

#  Sprawdzenie, czy suma brutto została podana,
#  a następnie wyliczenie i informacja, jeśli wartość netto (z pola)
#  znacznie odbiega od przeliczenia brutto × 0.77.
# if invoice_amount_gross > 0:
#     diff = abs(invoice_amount - invoice_net_from_gross)
#     if diff > 50:
#         st.sidebar.info(
#             f"Netto (pole) różni się od (brutto × 0.77) o ~**{diff:,.0f} PLN**."
#         )

num_people = st.sidebar.slider(
    "Liczba osób na Powołaniu", 1, 2, 2)

monthly_appointment_brutto = st.sidebar.number_input(
    "Wynagrodzenie Brutto z Powołania (na osobę)", value=10000)

st.sidebar.subheader("📉 Koszty i Wydatki")
co_costs = st.sidebar.number_input(
    "Koszty Spółki (Księgowość/Biuro)", value=1000)
living_expenses = st.sidebar.number_input("Koszty Życia (Rodzina)", value=8000)
mama_support = st.sidebar.number_input("Inne", value=0000)
benefit_800plus = st.sidebar.number_input("Świadczenia (np. 800+)", value=1600)

st.sidebar.subheader("🏦 IKZE (2 osoby / prognoza)")
ikze_enabled = st.sidebar.checkbox("Uwzględniaj IKZE w budżecie", value=True)
ikze_monthly_per_person = st.sidebar.number_input(
    "Wpłata IKZE (PLN/mies. na osobę)", min_value=0, value=942, step=10
)

# Metale Szlachetne
if st.sidebar.button("Aktualizuj ceny rynkowe"):
    st.cache_data.clear()

gold_price_live, exchange_rate = get_gold_price_pln()
silver_price_live = get_silver_price_pln()

st.sidebar.markdown("**Bieżące kursy metali**")
st.sidebar.write(f"Złoto: **{gold_price_live:,.2f} PLN/oz**")
st.sidebar.write(f"Srebro: **{silver_price_live:,.2f} PLN/oz**")
st.sidebar.write(f"Kurs USD/PLN: **{exchange_rate:.4f}**")

gold_price_oz = st.sidebar.number_input(
    "Cena uncji złota (PLN) do wyliczeń", value=gold_price_live)

st.sidebar.subheader("🟡 Złoto (założenia)")
corp_buy_gold_enabled = st.sidebar.checkbox(
    "Kupuj złoto z nadwyżki spółki", value=False
)
priv_buy_gold_enabled = st.sidebar.checkbox(
    "Kupuj złoto z nadwyżki prywatnej", value=True
)
gold_oz_per_year = st.sidebar.number_input(
    "Zakup złota (oz/rok)", min_value=0.0, value=2.0, step=0.25
)

st.sidebar.subheader("🛟 Poduszka finansowa")
emergency_fund_target = st.sidebar.number_input(
    "Cel poduszki (PLN)", min_value=0, value=50000, step=5000
)
emergency_fund_share_pct = st.sidebar.slider(
    "Ile % nadwyżki idzie na poduszkę", 0, 100, 40
)

# --- OBLICZENIA ---

# 1. Przeliczenie Powołania (Prywatnie)
payout_net_per_person, health_per_person, tax_per_person = calculate_net_appointment(
    monthly_appointment_brutto)
total_private_income = (payout_net_per_person * num_people) + benefit_800plus
ikze_monthly_total = (ikze_monthly_per_person * num_people) if ikze_enabled else 0
private_surplus = total_private_income - living_expenses - mama_support - ikze_monthly_total

# 2. Przeliczenie Spółki (Wynagrodzenie z powołania to koszt uzyskania przychodu - KUP)
total_appointment_cost_corp = monthly_appointment_brutto * num_people
# Podstawa przychodu do dalszych obliczeń = "netto razem" (netto + brutto*0.77)
profit_before_tax = invoice_net_total - total_appointment_cost_corp - co_costs

if profit_before_tax > 0:
    cit_tax = profit_before_tax * 0.09
    company_net_surplus = profit_before_tax - cit_tax
else:
    cit_tax = 0
    company_net_surplus = 0

# --- WIDOK GŁÓWNY (DASHBOARD) ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Nadwyżka Spółki", f"{company_net_surplus:,.0f} PLN")
col2.metric("Nadwyżka Prywatna", f"{private_surplus:,.0f} PLN")
col3.metric("Twoje Netto (os.)", f"{payout_net_per_person:,.0f} PLN")
col4.metric("Zdrowotna 9% (os.)",
            f"{health_per_person:,.0f} PLN", delta_color="inverse")

st.divider()

tab_analysis, tab_ikze, tab_gold, tab_loan = st.tabs(
    ["📊 Analiza Finansowa", "🏦 IKZE", "✨ Portfel Złota", "🏠 Spłata Domu"])

with tab_analysis:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏢 Finanse Spółki")
        st.write(f"Przychód Netto (pole): **{invoice_amount:,.0f} PLN**")
        st.write(f"Przychód Brutto: **{invoice_amount_gross:,.0f} PLN**")
        st.write(f"Przychód do obliczeń (netto razem): **{invoice_net_total:,.0f} PLN**")
        st.write(
            f"Koszty powołania: **{total_appointment_cost_corp:,.0f} PLN**")
        st.write(f"Zysk do opodatkowania: **{profit_before_tax:,.0f} PLN**")
        st.write(f"Podatek CIT (9%): **{cit_tax:,.0f} PLN**")
        st.info("💡 Wynagrodzenie zarządu (powołanie) obniża podatek CIT spółki.")

    with c2:
        st.subheader("🏠 Budżet Domowy")
        st.write(
            f"Wpływy Netto (Rodzina): **{total_private_income:,.0f} PLN**")
        st.write(
            f"Wydatki Stałe: **{living_expenses + mama_support:,.0f} PLN**")
        if ikze_enabled:
            st.write(f"IKZE (łącznie): **{ikze_monthly_total:,.0f} PLN**")
        st.success(f"Dostępna Nadwyżka: **{private_surplus:,.0f} PLN**")

    # Timeline akumulacji miesiąc po miesiącu (start: kwiecień 2026)
    st.subheader("⏱ Skumulowany Kapitał miesiąc po miesiącu (od kwietnia 2026)")
    months_sim = st.slider("Horyzont czasowy (miesiące)", 1, 360, 120)

    dates = pd.date_range(start="2026-04-01", periods=months_sim, freq="MS")
    date_keys = [d.strftime("%Y-%m") for d in dates]
    monthly_corp = max(company_net_surplus, 0)
    monthly_priv = max(private_surplus, 0)

    # Wartości estymowane (narastająco) z priorytetem budowy poduszki (prywatnie)
    corp_cum = []
    priv_cum = []
    total_cum = []
    emergency_cum = []
    investable_cum = []
    corp_cash_cum = []
    corp_gold_oz_cum = []
    corp_gold_value_cum = []
    priv_cash_cum = []
    priv_gold_oz_cum = []
    priv_gold_value_cum = []
    current_corp = 0.0
    current_priv = 0.0
    current_emergency = 0.0
    current_investable = 0.0
    current_corp_cash = 0.0
    current_corp_gold_oz = 0.0
    current_priv_cash = 0.0
    current_priv_gold_oz = 0.0
    for _ in range(months_sim):
        current_corp += monthly_corp
        current_priv += monthly_priv
        corp_cum.append(current_corp)
        priv_cum.append(current_priv)
        total_cum.append(current_corp + current_priv)

        available_priv = monthly_priv
        if (
            emergency_fund_target > 0
            and current_emergency < emergency_fund_target
            and available_priv > 0
            and emergency_fund_share_pct > 0
        ):
            to_emergency = min(
                available_priv * (emergency_fund_share_pct / 100.0),
                emergency_fund_target - current_emergency,
            )
        else:
            to_emergency = 0.0
        current_emergency += to_emergency
        investable_this_month = max(0.0, available_priv - to_emergency)

        # Nadwyżka prywatna: domyślnie zostaje jako gotówka do inwestycji; opcjonalnie zamieniana na złoto
        current_priv_cash += investable_this_month
        if priv_buy_gold_enabled and gold_oz_per_year > 0 and gold_price_oz > 0:
            planned_oz_month = gold_oz_per_year / 12.0
            planned_cost = planned_oz_month * gold_price_oz
            if current_priv_cash >= planned_cost:
                current_priv_cash -= planned_cost
                current_priv_gold_oz += planned_oz_month

        # "Do inwestycji" = prywatna gotówka + prywatne złoto (w PLN), bez spółki
        current_investable = current_priv_cash + (current_priv_gold_oz * gold_price_oz)
        emergency_cum.append(current_emergency)
        investable_cum.append(current_investable)
        priv_cash_cum.append(current_priv_cash)
        priv_gold_oz_cum.append(current_priv_gold_oz)
        priv_gold_value_cum.append(current_priv_gold_oz * gold_price_oz)

        # Nadwyżka spółki: zostaje na koncie; opcjonalnie zamieniana na złoto inwestycyjne
        current_corp_cash += monthly_corp
        if corp_buy_gold_enabled and gold_oz_per_year > 0 and gold_price_oz > 0:
            planned_oz_month = gold_oz_per_year / 12.0
            planned_cost = planned_oz_month * gold_price_oz
            if current_corp_cash >= planned_cost:
                current_corp_cash -= planned_cost
                current_corp_gold_oz += planned_oz_month
        corp_cash_cum.append(current_corp_cash)
        corp_gold_oz_cum.append(current_corp_gold_oz)
        corp_gold_value_cum.append(current_corp_gold_oz * gold_price_oz)

    # Wartości aktualne z mini-bazy JSON (narastająco z wpisanych miesięcznych kwot)
    actuals = load_actuals()
    corp_actual_cum = []
    priv_actual_cum = []
    total_actual_cum = []
    acc_corp = 0.0
    acc_priv = 0.0
    for key in date_keys:
        if key in actuals:
            rec = actuals[key]
            acc_corp += float(rec.get("spolka", 0))
            acc_priv += float(rec.get("prywatnie", 0))
        corp_actual_cum.append(acc_corp if actuals else None)
        priv_actual_cum.append(acc_priv if actuals else None)
        total_actual_cum.append(acc_corp + acc_priv if actuals else None)

    # Tabela: estymowane + aktualne (gdzie są)
    timeline_df = pd.DataFrame(
        {
            "Data": date_keys,
            "Spółka (est.)": corp_cum,
            "Prywatnie (est.)": priv_cum,
            "Łącznie (est.)": total_cum,
            "Poduszka (est.)": emergency_cum,
            "Do inwestycji (prywatnie est.)": investable_cum,
            "Prywatnie: gotówka (est.)": priv_cash_cum,
            "Prywatnie: złoto (oz est.)": priv_gold_oz_cum,
            "Prywatnie: złoto (PLN est.)": priv_gold_value_cum,
            "Spółka: konto (est.)": corp_cash_cum,
            "Spółka: złoto (oz est.)": corp_gold_oz_cum,
            "Spółka: złoto (PLN est.)": corp_gold_value_cum,
        }
    )
    if actuals:
        timeline_df["Spółka (akt.)"] = corp_actual_cum
        timeline_df["Prywatnie (akt.)"] = priv_actual_cum
        timeline_df["Łącznie (akt.)"] = total_actual_cum

    chart_df = timeline_df.set_index("Data")
    st.line_chart(chart_df, height=260)
    st.dataframe(timeline_df)

    # Wpisywanie wartości aktualnych i zapis do JSON
    st.subheader("📝 Wartości aktualne (zapis do mini-bazy JSON)")
    st.caption("Dla wybranego miesiąca wpisz faktyczne nadwyżki (spółka / prywatnie). Zapis w pliku: `data/actuals.json`.")
    col_m, col_s, col_p, col_btn = st.columns([2, 2, 2, 1])
    with col_m:
        month_to_edit = st.selectbox("Miesiąc", options=date_keys, key="month_actual")
    with col_s:
        val_spolka = st.number_input("Spółka (PLN)", value=0, step=500, key="val_spolka")
    with col_p:
        val_prywatnie = st.number_input("Prywatnie (PLN)", value=0, step=500, key="val_prywatnie")
    with col_btn:
        st.write("")
        st.write("")
        if st.button("Zapisz do bazy"):
            actuals[month_to_edit] = {"spolka": val_spolka, "prywatnie": val_prywatnie}
            save_actuals(actuals)
            st.success("Zapisano.")
            st.rerun()

with tab_ikze:
    st.subheader("🏦 IKZE")
    if not ikze_enabled:
        st.info("IKZE jest wyłączone w parametrach w sidebarze (nie jest odliczane od nadwyżki).")
    else:
        st.success("IKZE jest włączone i **odliczane od nadwyżki prywatnej**.")

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Wpłata / osoba (mies.)", f"{ikze_monthly_per_person:,.0f} PLN")
    with m2:
        st.metric("Wpłata łącznie (mies.)", f"{ikze_monthly_total:,.0f} PLN")
    with m3:
        st.metric("Wpłata łącznie (rok)", f"{ikze_monthly_total * 12:,.0f} PLN")

    months_ikze = st.slider("Horyzont IKZE (miesiące)", 1, 360, 120, key="months_ikze")
    dates_ikze = pd.date_range(start="2026-04-01", periods=months_ikze, freq="MS")
    keys_ikze = [d.strftime("%Y-%m") for d in dates_ikze]
    monthly_ikze = ikze_monthly_total if ikze_enabled else 0

    ikze_cum = []
    acc = 0.0
    for _ in range(months_ikze):
        acc += monthly_ikze
        ikze_cum.append(acc)

    ikze_df = pd.DataFrame({"Data": keys_ikze, "IKZE (wpłaty narastająco)": ikze_cum}).set_index("Data")
    st.line_chart(ikze_df, height=260)

with tab_gold:
    st.subheader("🟡 Złoto jako Aktywo Rezerwowe")
    st.write(
        f"Założenie: kupujesz rocznie: **{gold_oz_per_year:.2f} uncji** (koszt ~**{gold_oz_per_year * gold_price_oz:,.0f} PLN/rok**).")

    growth_rate = st.slider(
        "Przewidywany roczny wzrost ceny złota (%)", 0, 15, 7)
    future_years = 12  # do Twojej 50-tki
    future_price = gold_price_oz * ((1 + growth_rate/100)**future_years)

    st.write(
        f"Prognozowana cena uncji za {future_years} lat: **{future_price:,.0f} PLN**")
    total_oz = gold_oz_per_year * future_years
    st.success(
        f"Twój skarbiec w 2038 r.: **{total_oz:.1f} uncji** o wartości **{total_oz * future_price:,.0f} PLN**.")

    st.divider()
    st.subheader("📈 Historia cen złota i srebra (PLN)")
    metals_df = get_metals_history_df()
    if not metals_df.empty:
        st.line_chart(metals_df, height=260)
        st.caption("Dane: ostatnie 12 miesięcy, przeliczone na PLN po USD/PLN.")
        st.dataframe(metals_df.tail(12))

with tab_loan:
    st.subheader("🏠 Przyspieszona Spłata Kredytu")
    loan_val = st.number_input("Kapitał kredytu do spłaty", value=800000)
    overpay_amount = st.slider("Miesięczna nadpłata z nadwyżki prywatnej", 0, int(
        max(private_surplus, 0)), int(private_surplus * 0.7))

    if overpay_amount > 0:
        months_to_pay = loan_val / overpay_amount
        st.warning(
            f"Przy nadpłatach {overpay_amount:,.0f} PLN spłacisz dom w **{months_to_pay/12:.1f} lat**.")
        st.caption("Oszczędzasz na odsetkach i uciekasz z kosztów TBS/najmu.")

st.divider()
st.caption("Compliance Check: Powołanie (Art. 201 KSH) - Składka Zdrowotna 9% | PIT 12/32% | Kwota Wolna 30k. Stan na 2026.")
