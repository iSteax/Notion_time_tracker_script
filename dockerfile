# Use the official Python runtime as a parent image
FROM python:3.9

# Set the timezone
ENV TZ=America/Sao_Paulo
RUN apt-get update && apt-get install -y tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Set work directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install sqlite3
RUN apt-get update && apt-get install -y sqlite3

# Make port 80 available to the world outside this container (if needed)
# EXPOSE 80


# Define an environment variable (if needed)
# ENV NAME World

# Give execute permissions to the shell script
RUN chmod +x run_main_and_recieve_data_from_django_app.sh

# Command to run the shell script
CMD ["./run_main_and_recieve_data_from_django_app.sh"]