-- Insert devices
INSERT INTO fd_list (name, latitude, longitude) VALUES
('DeviceA', 55.7558, 37.6173),
('DeviceB', 48.8566, 2.3522),
('DeviceC', 40.7128, -74.0060);

-- Insert measurements for DeviceA (5 measurements, 4 frequencies each)
-- Measurement 1
INSERT INTO measurements (device_id, timestamp, frequency, rssi) VALUES
(1, '2023-01-01 00:00:00+00', 900000000, -53),
(1, '2023-01-01 00:00:00+00', 2400000000, -26),
(1, '2023-01-01 00:00:00+00', 5200000000, -64),
(1, '2023-01-01 00:00:00+00', 5800000000, -55);

-- Measurement 2
INSERT INTO measurements (device_id, timestamp, frequency, rssi) VALUES
(1, '2023-01-01 00:01:00+00', 900000000, -48),
(1, '2023-01-01 00:01:00+00', 2400000000, -30),
(1, '2023-01-01 00:01:00+00', 5200000000, -70),
(1, '2023-01-01 00:01:00+00', 5800000000, -50);

-- Measurement 3
INSERT INTO measurements (device_id, timestamp, frequency, rssi) VALUES
(1, '2023-01-01 00:02:00+00', 900000000, -55),
(1, '2023-01-01 00:02:00+00', 2400000000, -28),
(1, '2023-01-01 00:02:00+00', 5200000000, -65),
(1, '2023-01-01 00:02:00+00', 5800000000, -52);

-- Measurement 4
INSERT INTO measurements (device_id, timestamp, frequency, rssi) VALUES
(1, '2023-01-01 00:03:00+00', 900000000, -50),
(1, '2023-01-01 00:03:00+00', 2400000000, -25),
(1, '2023-01-01 00:03:00+00', 5200000000, -68),
(1, '2023-01-01 00:03:00+00', 5800000000, -48);

-- Measurement 5
INSERT INTO measurements (device_id, timestamp, frequency, rssi) VALUES
(1, '2023-01-01 00:04:00+00', 900000000, -52),
(1, '2023-01-01 00:04:00+00', 2400000000, -27),
(1, '2023-01-01 00:04:00+00', 5200000000, -66),
(1, '2023-01-01 00:04:00+00', 5800000000, -54);

-- Insert for DeviceB (similar, timestamps from 00:05:00, RSSI varied -60 to -20)
-- Measurement 1 for DeviceB
INSERT INTO measurements (device_id, timestamp, frequency, rssi) VALUES
(2, '2023-01-01 00:05:00+00', 900000000, -60),
(2, '2023-01-01 00:05:00+00', 2400000000, -35),
(2, '2023-01-01 00:05:00+00', 5200000000, -75),
(2, '2023-01-01 00:05:00+00', 5800000000, -55);

-- Continue for measurements 2-5 for DeviceB...

-- Insert for DeviceC (timestamps from 00:10:00, RSSI -80 to -40)
-- Measurement 1 for DeviceC
INSERT INTO measurements (device_id, timestamp, frequency, rssi) VALUES
(3, '2023-01-01 00:10:00+00', 900000000, -80),
(3, '2023-01-01 00:10:00+00', 2400000000, -45),
(3, '2023-01-01 00:10:00+00', 5200000000, -85),
(3, '2023-01-01 00:10:00+00', 5800000000, -65);

-- Continue for measurements 2-5 for DeviceC...
