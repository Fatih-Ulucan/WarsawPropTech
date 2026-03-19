--  PROPERTY TYPES 
CREATE TABLE property_types (
                                type_id SERIAL PRIMARY KEY,
                                type_name_en VARCHAR(50),
                                type_name_pl VARCHAR(50)
);

INSERT INTO property_types (type_name_en, type_name_pl) VALUES
                                                            ('Apartment', 'Mieszkanie'),
                                                            ('Commercial/Retail', 'Lokal użytkowy'),
                                                            ('Land', 'Działka'),
                                                            ('Office', 'Biuro'),
                                                            ('WareHouse', 'Magazyn'),
                                                            ('Garage', 'Garaż');

-- TRANSACTION TYPES 

CREATE TABLE transaction_types (
                                   trans_id SERIAL PRIMARY KEY ,
                                   trans_name_en VARCHAR(50),
                                   trans_name_pl VARCHAR(50)
);

INSERT INTO transaction_types (trans_name_en, trans_name_pl) VALUES
                                                                 ('For Sale', 'Sprzedaż'),
                                                                 ('For Rent' , 'Wynajem');

-- LOCATIONS 

CREATE TABLE locations (
                           loc_id SERIAL PRIMARY KEY ,
                           city VARCHAR(50) DEFAULT 'Warszawa',
                           district  VARCHAR(50) NOT NULL
);

INSERT INTO locations (district) VALUES
                                     ('Mokotów'), ('Praga-Południe'), ('Ursynów'), ('Wola'),
                                     ('Białołęka'), ('Bielany'), ('Bemowo'), ('Targówek'),
                                     ('Śródmieście'), ('Wawer'), ('Ochota'), ('Ursus'),
                                     ('Praga-Północ'), ('Włochy'), ('Wilanów'), ('Wesoła'),
                                     ('Żoliborz'), ('Rembertów');

-- AGENCIES 

CREATE TABLE agencies (
                          agency_id SERIAL PRIMARY KEY,
                          agency_name VARCHAR(150),
                          agency_number VARCHAR(20),
                          is_private_seller BOOLEAN DEFAULT FALSE
);

-- PROPERTIES 

CREATE TABLE properties (
                            property_id SERIAL PRIMARY KEY,
                            loc_id INTEGER REFERENCES locations(loc_id),
                            type_id INTEGER REFERENCES property_types(type_id),
                            area_sqm DECIMAL(10,2),
                            rooms_count INTEGER,
                            floor_number INTEGER,
                            build_year INTEGER,
                            property_condition VARCHAR(50),
                            distance_to_metro_m INTEGER,
                            distance_to_tram_m INTEGER,
                            distance_to_bus_m INTEGER,
                            distance_to_market_m INTEGER,
                            distance_to_centrum_km DECIMAL(5,2)
);
-- LISTINGS

CREATE TABLE listings (
                          listing_id SERIAL PRIMARY KEY ,
                          property_id INTEGER REFERENCES  properties(property_id),
                          agency_id INTEGER REFERENCES agencies(agency_id),
                          trans_id INTEGER REFERENCES transaction_types(trans_id),
                          price_pln DECIMAL(15,2),
                          price_per_sqm DECIMAL(15,2),
                          url_link TEXT UNIQUE,
                          source_platform VARCHAR(50),
                          is_active BOOLEAN DEFAULT TRUE,
                          created_at TIMESTAMP DEFAULT  CURRENT_TIMESTAMP,
                          updated_at TIMESTAMP DEFAULT  CURRENT_TIMESTAMP

);

--PRICE HISTORY
CREATE TABLE price_history(
                              history_id SERIAL PRIMARY KEY ,
                              listing_id INTEGER REFERENCES listings(listing_id),
                              old_price_pln DECIMAL(15,2) NOT NULL ,
                              new_price_pln DECIMAL(15,2) NOT NULL,
                              change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

--MARKET STATS
CREATE TABLE market_stats(
                             stat_id SERIAL PRIMARY KEY ,
                             loc_id INTEGER REFERENCES  locations(loc_id),
                             type_id INTEGER REFERENCES property_types(type_id),
                             avg_price_sale_sqm DECIMAL(10,2),
                             avg_price_rent_sqm DECIMAL(10,2),
                             avg_days_on_market INTEGER,
                             calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

--SUBSCRIBERS
CREATE TABLE subscribers(
                            sub_id SERIAL PRIMARY KEY ,
                            full_name VARCHAR(100) NOT NULL,
                            email VARCHAR(100) UNIQUE  NOT NULL ,
                            phone_number VARCHAR(20),
                            target_loc_id INTEGER REFERENCES locations(loc_id),
                            is_premium BOOLEAN DEFAULT FALSE ,
                            subscription_end_date DATE ,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

                                     
                                           