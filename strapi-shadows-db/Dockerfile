FROM node:16
# Installing libvips-dev for sharp Compatability
RUN apt-get update && apt-get install libvips-dev -y
RUN apt-get install -y --no-install-recommends \
        awscli \
	cron 
ARG NODE_ENV=development
ENV NODE_ENV=${NODE_ENV}
RUN mkdir /root/.aws
WORKDIR /opt/
COPY ./package.json ./package-lock.json ./
COPY ./container_cronjob /etc/cron.d/container_cronjob
RUN chmod 0644 /etc/cron.d/container_cronjob \
       && crontab /etc/cron.d/container_cronjob
ENV PATH /opt/node_modules/.bin:$PATH
RUN npm install
WORKDIR /opt/app
COPY ./ .
RUN npm run build
EXPOSE 1337
#CMD ["npm", "run", "develop"]
CMD ["/bin/bash", "-c", "cron && npm run develop"]

# first two covered by above `COPY ./ .` comand
#COPY ./config /opt/app/config
#COPY ./src /opt/app/src
COPY ./package.json /opt/package.json
COPY ./package-lock.json /opt/package-lock.json
