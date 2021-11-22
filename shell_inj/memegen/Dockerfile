FROM ruby:2.7.4-alpine

RUN apk add --no-cache imagemagick make gcc musl-dev fontconfig sqlite-dev
RUN gem install sinatra bcrypt sqlite3

COPY fonts/impact.ttf /usr/share/fonts/
RUN fc-cache /usr/share/fonts/

WORKDIR /app

COPY ./ ./

ENV APP_ENV production
CMD ["/usr/bin/env", "ruby", "./app.rb"]
