# 1. Imagem base com as dependências necessárias
FROM python:3.13-slim

# 2. Define o diretório de trabalho dentro do container
WORKDIR /BlockchainNode8000

# 3. Copia os arquivos da máquina local para o container
COPY requirements.txt .
COPY BlockchainNode8000/ .

# 4. Instala as dependências Python
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgl1-mesa-glx\
    libzbar0

RUN pip install --no-cache-dir -r requirements.txt

# 5. Expõe a porta usada pelo FastAPI
EXPOSE 8000

# 6. Comando para rodar o app FastAPI com uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]