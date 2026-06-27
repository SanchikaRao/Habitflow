# Step 1: Use an official lightweight Python runtime as a base image
FROM python:3.11-slim

# Step 2: Set the working directory inside the container structure
WORKDIR /code

# Step 3: Copy the requirements file over and install dependencies
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Step 4: Copy the rest of your application code files inside the container
COPY . /code

# Step 5: Run the production application server launch script
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]