FROM ruby:2.7.4-alpine

RUN apk add --no-cache imagemagick make gcc musl-dev fontconfig sqlite-dev 
RUN gem install sinatra bcrypt sqlite3 

RUN apk add --update --no-cache build-base imagemagick6 imagemagick6-c++ \
    imagemagick6-dev imagemagick6-libs

RUN gem install rmagick

COPY fonts/impact.ttf /usr/share/fonts/
RUN fc-cache /usr/share/fonts/

WORKDIR /app

COPY ./ ./

ENV APP_ENV production
CMD ["/usr/bin/env", "ruby", "./app.rb"]
