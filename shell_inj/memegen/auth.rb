require 'bcrypt'
require 'sqlite3'

module Auth

  def Auth.password_hash(pwd)
    BCrypt::Password.create(pwd).to_s
  end

  class User
    attr_reader :id, :username

    def initialize(id, username, pwd_hash)
      @id = id
      @username = username
      @password_hash = pwd_hash
    end

    def test_password(password)
      BCrypt::Password.new(@password_hash) == password
    end
  end

  class Storage
    def initialize(path = "users.sqlite3")
      @db = SQLite3::Database.new(path)
      @db.execute <<-SQL
        create table if not exists Users
          ( rowid integer primary key
          , name text unique
          , password text
          )
      SQL
    end

    def add_user(name, password)
      pwd_hash = Auth.password_hash password
      begin
        @db.execute("insert into Users (name, password ) values (?, ?)", [name, pwd_hash])
      rescue SQLite3::ConstraintException
        # user already exists
        return nil
      end
      @db.execute("select rowid from Users where name = ?", [name]) do |row|
        return row[0]
      end
    end

    def user_by_id(id)
      @db.execute("select rowid, name, password from Users where rowid = ?", [id]) do |row|
        return User.new(row[0], row[1], row[2])
      end
      nil
    end

    def user_by_name(name)
      @db.execute("select rowid, name, password from Users where name = ?", [name]) do |row|
        return User.new(row[0], row[1], row[2])
      end
      nil
    end
  end

end
