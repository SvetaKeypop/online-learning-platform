FROM nginx:alpine

RUN rm /etc/nginx/conf.d/default.conf || true

COPY nginx.conf /etc/nginx/nginx.conf
COPY static /usr/share/nginx/html

EXPOSE 80
