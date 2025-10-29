# CLONE REPO

mkdir projects > cd projects

git clone https://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####@github.com/mutesasiratimo/kcca_kla_connect_api

# Make VENV

python3 -m venv fastapi_env

# ACTIVATE VENV

source fastapi_env/bin/activate

# CHECK WHICH PIP

where pip

IF NOT:
sudo apt install pip or 
sudo apt install python3-pip

# SETUP OPEN SSH

sudo apt install openssh-server

sudo apt install ufw

sudo ufw enable

sudo ufw allow ssh

sudo systemctl enable ssh

sudo systemctl status ssh

sudo apt install python3-tk

sudo apt install gunicorn

# SETUP POSTGRESQL

sudo apt install wget ca-certificates

wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" >> /etc/apt/sources.list.d/pgdg.list'

sudo apt update

sudo apt install postgresql postgresql-contrib

sudo systemctl status postgresql

sudo -u postgres psql

\password postgres

CREATE DATABASE klaconnect;

\c klaconnect

exit

sudo nano /etc/postgresql/17/main/postgresql.conf

Uncomment and edit the listen_addresses attribute to start listening to start listening to all available IP addresses.

listen_addresses = '\*'

sudo nano /etc/postgresql/17/main/pg_hba.conf

Append a new connection policy (a pattern stands for [CONNECTION_TYPE][DATABASE][USER] [ADDRESS][METHOD]) in the bottom of the file.

host all all 0.0.0.0/0 md5

sudo systemctl restart postgresql

ss -nlt | grep 5432

# INSTALL FAST API DEPENDENCIES

pip install fastapi[all]
pip install httptools==0.1.1
pip install databases
pip install asyncpg
pip install psycopg2-binary
pip install pyJWT
pip install python-decouple
pip install DateTime
pip install fastapi_pagination
pip install fastapi_mail

# NGINX CONFIGURATION SETUP

sudo apt install nginx

sudo systemctl start nginx

sudo systemctl enable nginx

sudo nano /etc/nginx/sites-available/kcca

paste text below

###########################

server {
listen 80;
server_name 172.16.0.159;

    #index index.html;
    #root /var/www/html/mywebsite;

    location / {

        alias /home/timo/html/klakonnect;

    }


    location ^~ /apiklakonnect/ {
        #allow 127.0.0.1;
        proxy_pass http://127.0.0.1:6000/;

    }

}

###########################

server {
listen 80;
server_name 172.16.0.159;

    #index index.html;
    #root /var/www/html/mywebsite;

    location /klakonnect {

        alias /home/timo/html/klakonnect;

    }

    location /dmmp {

        alias /home/timo/html/dmmp;

    }

    location /drammp {

        alias /home/timo/html/drammp;

    }

    location ^~ /apiklakonnect/ {
        #allow 127.0.0.1;
        proxy_pass http://127.0.0.1:6000/;

    }

    location ^~ /apidmmp/ {
        #allow 127.0.0.1;
        proxy_pass http://127.0.0.1:8000/;

    }

    location ^~ /apidrammp/ {
        #allow 127.0.0.1;
        proxy_pass http://127.0.0.1:5000/;

    }

}

#############################

# SETUP NGINX SYM LINK

sudo ln -s /etc/nginx/sites-available/kcca /etc/nginx/sites-enabled/

# ALLOW NGINX VIA UFW

sudo ufw allow 'Nginx Full'

# SETUP APPLICATON TO RUN AS SERVICE

sudo nano /etc/systemd/system/klakonnect.service

paste text below \*\* check spelling difference btn kla_konnect and kla_connect

[Unit]
Description=Gunicorn instance to serve MyApp
After=network.target

[Service]
User=mutestimo72
Group=www-data
WorkingDirectory=/home/mutestimo72/projects/kcca_kla_connect_api
Environment="PATH=/usr/local/bin"
#ExecStart=/usr/bin/gunicorn -k uvicorn.workers.UvicornWorker main:app
ExecStart=/home/mutestimo72/fastapi_env/bin/uvicorn main:app --host 0.0.0.0 --port 6000 --root-path="/apiklakonnect"
Restart=always

[Install]
WantedBy=multi-user.target

//////

sudo systemctl start klakonnect

sudo systemctl enable klakonnect

sudo systemctl restart klakonnect

# SETUP LOGGING (OPTIONAL)

cd projects/kla_connect_api/

sudo nano gunicorn.conf

paste text below:
########################

from multiprocessing import cpu_count

# Socket Path

bind = 'unix:/root/project/kcca_kla_connect_api/gunicorn.sock'

# Worker Options

workers = cpu_count() + 1
worker_class = 'uvicorn.workers.UvicornWorker'

# Logging Options

loglevel = 'debug'
accesslog = '/home/timo/projects/kcca_kla_connect_api/access_log'
errorlog = '/home/timo/projects/kcca_kla_connect_api/error_log'

///////

GNU nano 6.2 /etc/systemd/system/klakonnect.service  
[Unit]
Description=Gunicorn instance to serve KLA Konnect API
After=network.target

[Service]
User=timo
Group=www-data
WorkingDirectory=/home/timo/projects/kcca_kla_connect_api
Environment="PATH=/home/timo/projects/fastapi_env/bin"
ExecStart=/home/timo/projects/fastapi_env/bin/gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:6000 --env UVICORN_CMD_ARGS="--root-path /apiklakonnect"

#ExecStart=/home/timo/projects/fastapi_env/bin/uvicorn main:app --host 0.0.0.0 --port 6000 --root-path="/apiklakonnect"
Restart=always

[Install]
WantedBy=multi-user.target



my web dashboard is only loading metadata, but timing out

this is my nginx proxy config, is it right?

server {
listen 80;
server_name 172.16.0.159;

    index index.html;
    root /var/www/html;

    location / {

        try_files $uri /index.html;

    }


    location ^~ /apiklakonnect/ {
        #allow 127.0.0.1;
        proxy_pass http://127.0.0.1:7000/;

    }

}