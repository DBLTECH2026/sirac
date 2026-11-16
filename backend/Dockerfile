FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
# Los modelos se entrenan al construir la imagen (datos simulados con semilla fija = siempre el mismo resultado)
RUN python -m ia.ml.entrenar && python manage.py collectstatic --noinput
RUN useradd --create-home sirac && chown -R sirac /app
USER sirac
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/salud', timeout=4)"
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py crm_demo && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60 --access-logfile -"]
