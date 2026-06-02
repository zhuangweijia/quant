#!/bin/sh
set -e

if [ "${NGINX_SSL_ENABLED}" = "true" ] && [ -f /etc/nginx/ssl/fullchain.pem ] && [ -f /etc/nginx/ssl/privkey.pem ]; then
    echo "SSL enabled: using nginx.ssl.conf"
    cp /etc/nginx/conf.d/nginx.ssl.conf /etc/nginx/conf.d/default.conf
    rm /etc/nginx/conf.d/nginx.ssl.conf
else
    echo "SSL not enabled: using nginx.conf (HTTP)"
    rm -f /etc/nginx/conf.d/nginx.ssl.conf
fi

exec nginx -g "daemon off;"
