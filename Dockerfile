# TemplateBot/Dockerfile

# Use uma imagem base oficial do Python
FROM python:3.9-slim

# Defina o diretório de trabalho no contêiner
WORKDIR /usr/src/app

# Copie o arquivo de dependências para o diretório de trabalho
COPY requirements.txt ./

# Instale as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copie o restante dos arquivos do seu bot para o diretório de trabalho
COPY . .

# Comando para iniciar o bot quando o contêiner for executado
CMD ["python", "app.py"]