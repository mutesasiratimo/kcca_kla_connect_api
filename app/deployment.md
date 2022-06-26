git clone https://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@github.com/mutesasiratimo/kcca_kla_connect_api


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