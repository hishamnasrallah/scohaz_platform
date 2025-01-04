FROM python:3.12 as backend

# Set up working directory
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

# Update apt-get and install required packages
RUN apt-get update
RUN apt-get install -y gettext xmlsec1 curl

# Upgrade pip
RUN pip install --upgrade pip

# Install gunicorn
RUN pip3 install --no-cache-dir gunicorn

# Copy requirements and install dependencies
COPY requirements.txt /usr/src/app/
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /usr/src/app/

# List files in /usr/src/app to verify manage.py exists
RUN ls -al /usr/src/app

# Collect static files
RUN ls -al /usr/src/app/
RUN python /usr/src/app/manage.py collectstatic --noinput --clear

# Static Stage (NGINX)
FROM nginx:1.20.0 as statics
COPY --from=backend /usr/src/app/static_root /usr/share/nginx/html/static
RUN chmod 777 -R /usr/share/nginx/html/static
