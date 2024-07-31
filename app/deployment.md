git clone https://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@github.com/mutesasiratimo/kcca_kla_connect_api

# Make VENV

python3 -m venv fastapi_env

# ACTIVATE VENV

source fastapi_env/bin/activate

# CHECK WHICH PIP

where pip

# IF NOT, INSTALL PIP

sudo apt install python3-tk

sudo apt install gunicorn

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

//NGINX SITES SCRIPT
server{

    server_name 172.16.0.160;

    location / {
        allow 127.0.0.1;
        include proxy_params;
        proxy_pass http://127.0.0.1:8000;
    }

location /dashboard {
alias /home/agnes/html/dashboard;

        # any additional configuration for non-static content

}

}

///gunicorn.conf
from multiprocessing import cpu_count

# Socket Path

bind = 'unix:/root/project/kcca_kla_connect_api/gunicorn.sock'

# Worker Options

workers = cpu_count() + 1
worker_class = 'uvicorn.workers.UvicornWorker'

# Logging Options

loglevel = 'debug'
accesslog = '/root/project/kcca_kla_connect_api/access_log'
errorlog = '/root/project/kcca_kla_connect_api/error_log'

///////

////project.service
[Unit]
Description=Gunicorn instance to serve MyApp
After=network.target

[Service]
User=mutestimo72
Group=www-data
WorkingDirectory=/home/mutestimo72/projects/kcca_dmmp_api
Environment="PATH=/usr/local/bin"
#ExecStart=/usr/bin/gunicorn -k uvicorn.workers.UvicornWorker main:app
ExecStart=/home/mutestimo72/fastapi_env/bin/uvicorn main:app --host 0.0.0.0 --port 6000
Restart=always

[Install]
WantedBy=multi-user.target

//////

LIVE SERVER NGINX CONFIG
164.92.157.80
server {
listen 443 ssl;
listen [::]:443 ssl;

      server_name 172.16.0.192 dmmp.kcca.go.ug;
      ssl_certificate /etc/nginx/ssl/wild/file2021.crt;
      ssl_certificate_key  /etc/nginx/ssl/wild/file2021.key;

      location /api {
        allow 127.0.0.1;
        include proxy_params;
        proxy_pass http://127.0.0.1:8000;

}
location /dashboard {
alias /home/special/html/dashboard;

        # any additional configuration for non-static content

}

}

[Unit]
Description=Gunicorn instance to serve MyApp
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/root/project/kcca_kla_connect_api
Environment="PATH=/usr/local/bin"
ExecStart=/usr/bin/gunicorn -k uvicorn.workers.UvicornWorker main:app

[Install]
WantedBy=multi-user.target
