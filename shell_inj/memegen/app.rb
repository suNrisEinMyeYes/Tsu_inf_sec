#!/usr/bin/env ruby
require 'sinatra'
require 'securerandom'
require './auth.rb'
require "rmagick"

enable :sessions
set :port, 3001

USERS = Auth::Storage.new

get "/" do
  erb :form
end

post "/save_image" do
  file = params[:my_file][:tempfile]
  temp_name = file.path
  input_name = params[:my_file][:filename]

  output_name = SecureRandom.uuid + File.extname(input_name)

  img = Magick::ImageList.new(temp_name)
  

  text = Magick::Draw.new
  
  text.annotate(img, 0,0,0,0, params[:top_text]) do
    text.gravity = Magick::NorthGravity
    self.pointsize = 50
    text.font = "/app/fonts/impact.ttf"
    self.font_weight = Magick::BoldWeight
    self.stroke = "none"
  end
  
  text.annotate(img, 0,0,0,0, params[:bottom_text]) do
    text.gravity = Magick::SouthGravity
    self.pointsize = 50
    text.font = "/app/fonts/impact.ttf"
    self.font_weight = Magick::BoldWeight
    self.stroke = "none"
  end

  print("DEBUG\n")
  puts(img.cur_image())
  puts(img[0]["info"])
  print("DEBUG\n")
  img.cur_image[:comment] = "{\"top\" : \"#{params[:top_text]}\", \"bot\" : \"#{params[:bottom_text]}\"}"

  img.write("public/uploads/" + output_name) # Destination image

  if current_user
    @filename = output_name
    erb :show_image
  else
    session[:redirect_to_image] = output_name
    redirect "/sign_in"
  end
end

get "/view_image" do
  @filename = session[:redirect_to_image]
  erb :show_image
end

get "/sign_in" do
  erb :sign_in
end

post "/sign_in" do
  user = USERS.user_by_name(params[:username])
  if user && user.test_password(params[:password])
    session[:user_id] = user.id
    redirect '/'
  else
    @error = 'Username or password was incorrect'
    erb :sign_in
  end
end

post '/register' do
  user_id = USERS.add_user(params[:username], params[:password])
  if user_id
    session[:user_id] = user_id
    after_login
  else
    @error = "Username already exists"
    erb :sign_in
  end
end

helpers do
  def current_user
    if session[:user_id]
       USERS.user_by_id(session[:user_id])
    else
      nil
    end
  end

  def after_login
    if session[:redirect_to_image]
      redirect "/view_image"
    else
      redirect "/"
    end
  end
end
