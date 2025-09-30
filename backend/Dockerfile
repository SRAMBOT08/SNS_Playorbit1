FROM python:3.10-slim

# set working directory
WORKDIR /app

# install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy app code
COPY ./app ./app

# run server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
