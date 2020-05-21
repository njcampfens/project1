import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# We create the connection to the DATABASE
engine = create_engine(os.getenv('DATABASE_URL'))
db = scoped_session(sessionmaker(bind=engine))

def main():
    # we open the csv file with the data
    f = open('books.csv')
    reader = csv.reader(f)

    # we save the data from the csv to the DATABASE
    i = 0
    for isbn, title, author, year in reader:
        db.execute('INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)',
                    {'isbn':isbn, 'title':title, 'author':author, 'year':int(year)})
        print(i)
        i += 1

    # commit the db transaction
    db.commit()

if __name__ == '__main__':
    main()
