# Use an official Python runtime as the parent image
FROM python:3.9-slim

# Set the timezone
ENV TZ=America/Sao_Paulo
RUN apt-get update && apt-get install -y tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container (if needed)
# EXPOSE 80

# Define an environment variable (if needed)
# ENV NAME World

# Run the Python script when the container launches
CMD ["python", "main.py"]
