# FIRE (Streamlit)

## Uruchomienie lokalnie

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m streamlit run app.py
```

## Uruchomienie przez Docker

```bash
docker build -t fire-streamlit .
docker run --rm -p 8501:8501 fire-streamlit
```

