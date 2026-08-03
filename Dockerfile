FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    libldap2-dev \
    libsasl2-dev \
    libjpeg-dev \
    zlib1g-dev \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    libssl-dev \
    libmagic1 \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff6 \
    libtiff-dev \
    libwebp-dev \
    libglib2.0-0 \
    poppler-utils \
    tesseract-ocr \
    ghostscript \
    node-less \
    npm \
    fonts-dejavu-core \
    fonts-liberation \
    && wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb -P /tmp \
    && apt-get install -y /tmp/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
    && rm /tmp/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/odoo

COPY . /opt/odoo

RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt \
    && pip install --no-cache-dir \
        Pillow \
        beautifulsoup4 \
        ddgs \
        duckduckgo_search \
        fake-useragent \
        lxml \
        numpy \
        pandas \
        pdf2image \
        pdfminer.six \
        pytesseract \
        python-docx \
        openpyxl \
        XlsxWriter \
        reportlab \
        RapidFuzz \
        requests-file \
        requests-toolbelt \
        scikit-learn \
        scipy \
        websocket-client \
        python-magic \
        pypdf \
        pdfplumber \
        opencv-python-headless \
        sentence-transformers \
        transformers \
        accelerate \
        huggingface-hub \
        chromadb \
        faiss-cpu

COPY ./debian/odoo.conf /etc/odoo.conf

EXPOSE 8069 8072

CMD ["python3", "odoo-bin", "-c", "/etc/odoo.conf"]
