# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
from django.db import models
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from apps.accounts.models import Profile
from apps.accounts.tables import UserTable
from apps.stations.models import Station

from django.utils import timezone
import os
import secrets
import string
import maidenhead as mh
from pathlib import Path

'''
EXAMPLE USAGE

python manage.py create_profile_and_station --username johndoe6 --email john@example.com --station_id N000014 --nickname "John's Station" --grid FN31pr --city "Los Angeles" --state "CA" --postal_code "90001" --antenna_1 "Test_antenna" --antenna_2 "NA" --street_address "1234 Nowhere Drive" --phone_number "123456789"
'''


def generate_random_string(length=32):
	characters = string.ascii_letters + string.digits
	return ''.join(secrets.choice(characters) for _ in range(length))


def generate_secure_password(length=25):
	"""Generates a secure random password with the given length."""
	characters = string.ascii_letters + string.digits + string.punctuation
	return ''.join(secrets.choice(characters) for _ in range(length))


class Command(BaseCommand):
	help = "Create a Profile and associated Station for a user, set up a directory, and output details to a text file"

	def add_arguments(self, parser):
		# User/Profile arguments
		parser.add_argument('--username', type=str, required=True, help="Username for the user")
		parser.add_argument('--email', type=str, required=True, help="Email for the user")

		# Make station_id a required argument
		parser.add_argument('--station_id', type=str, required=True, help="Station ID")

		# Station arguments
		parser.add_argument('--nickname', type=str, required=True, help="Station nickname")
		parser.add_argument('--grid', type=str, required=True, help="Maidenhead grid locator (e.g., FN31pr)")
		parser.add_argument('--elevation', type=float, help="Elevation of the station")
		parser.add_argument('--antenna_1', type=str, help="Primary antenna type")
		parser.add_argument('--antenna_2', type=str, help="Secondary antenna type")
		parser.add_argument('--street_address', type=str, help="Street address of the station")
		parser.add_argument('--city', type=str, help="City where the station is located")
		parser.add_argument('--state', type=str, help="State where the station is located")
		parser.add_argument('--postal_code', type=str, help="Postal code of the station")
		parser.add_argument('--phone_number', type=str, help="Phone number for the station")

	def handle(self, *args, **kwargs):
		# Validate that station_id is exactly 7 characters
		station_id = kwargs['station_id']
		if len(station_id) != 7:
			self.stdout.write(self.style.ERROR("The station_id must be exactly 7 characters long. Exiting."))
			return  # Exit the program if station_id is invalid

		# Directory paths for station
		station_dir_home = f"/home/{station_id}"
		station_dir_stations = f"/home/stations/{station_id}"

		# Check if the directory already exists in either location and indicate which one
		if os.path.exists(station_dir_home):
			self.stdout.write(self.style.ERROR(f"Directory already exists: {station_dir_home}. Exiting."))
			return  # Exit the program if the directory exists in /home/

		if os.path.exists(station_dir_stations):
			self.stdout.write(self.style.ERROR(f"Directory already exists: {station_dir_stations}. Exiting."))
			return  # Exit the program if the directory exists in /home/stations/

		# Extract User/Profile details
		username = kwargs['username']
		email = kwargs['email']

		# Generate a secure random password
		password = generate_secure_password()

		# Create or retrieve User
		user, created = User.objects.get_or_create(username=username, defaults={'email': email})
		if created:
			user.set_password(password)
			user.save()
			self.stdout.write(self.style.SUCCESS(f"User created for {username}"))
		else:
			self.stdout.write(self.style.WARNING(f"User {username} already exists"))

		# Create or retrieve Profile
		profile, profile_created = Profile.objects.get_or_create(
			user=user, defaults={'email': email, 'signup_confirmation': True}
		)
		if profile_created:
			self.stdout.write(self.style.SUCCESS(f"Profile created for {username}"))
		else:
			self.stdout.write(self.style.WARNING(f"Profile for user {username} already exists"))

		station_pass = generate_random_string()
		grid = kwargs.get('grid')

		try:
			# Convert Maidenhead grid to latitude and longitude
			latitude, longitude = mh.to_location(grid)
		except ValueError:
			self.stdout.write(self.style.ERROR(f"Invalid Maidenhead grid: {grid}. Exiting."))
			return

		# Extract Station details
		station_data = {
			'user': user,
			'station_id': station_id,
			'nickname': kwargs['nickname'],
			'grid': grid,
			'latitude': latitude,
			'longitude': longitude,
			'elevation': kwargs.get('elevation'),
			'antenna_1': kwargs.get('antenna_1'),
			'antenna_2': kwargs.get('antenna_2'),
			'street_address': kwargs.get('street_address'),
			'city': kwargs.get('city'),
			'state': kwargs.get('state'),
			'postal_code': kwargs.get('postal_code'),
			'phone_number': kwargs.get('phone_number'),
			'create_date': timezone.now(),
			'station_pass': station_pass
		}

		# Create Station
		station = Station.objects.create(**station_data)
		self.stdout.write(self.style.SUCCESS(f"Station '{station.nickname}' created for user {username}"))

		REPO_ROOT = Path(__file__).resolve().parents[5]
		STATION_CREATION_SCRIPT = str(REPO_ROOT / "scripts/ingest/stationcreation4.sh")

		# Run directory creation command
		os.system(f'sudo {STATION_CREATION_SCRIPT} {station.station_id} {station.station_pass}')
		self.stdout.write(self.style.SUCCESS(f"Directory created for station {station.station_id}"))
		
		# # No longer need jailing as of 2026
		# create_jail_script = "/bin/create_jail.sh"
		# try:
		# 	os.system(f"bash {create_jail_script} {station_id}")
		# 	self.stdout.write(self.style.SUCCESS(f"Jail created successfully for station ID: {station_id}"))
		# except Exception as e:
		# 	self.stdout.write(self.style.ERROR(f"Failed to create jail for station ID: {station_id}. Error: {e}"))

		# Prepare output file content
		output_content = (
			f"User and Profile Details\n"
			f"Username: {user.username}\n"
			f"Password: {password}\n"
			f"Email: {profile.email}\n"
			f"Signup Confirmation: {profile.signup_confirmation}\n\n"
			f"Station Details\n"
			f"Station ID: {station.station_id}\n"
			f"Nickname: {station.nickname}\n"
			f"Maidenhead Grid: {station.grid}\n"
			f"Latitude: {station.latitude}\n"
			f"Longitude: {station.longitude}\n"
			f"Elevation: {station.elevation}\n"
			f"Antenna 1: {station.antenna_1}\n"
			f"Antenna 2: {station.antenna_2}\n"
			f"Street Address: {station.street_address}\n"
			f"City: {station.city}\n"
			f"State: {station.state}\n"
			f"Postal Code: {station.postal_code}\n"
			f"Phone Number: {station.phone_number}\n"
			f"Created Date: {station.create_date}\n"
		)

		# Define the output directory and initial file path
		output_dir = "/home/user/user_creation_outputs"
		if not os.path.exists(output_dir):
			os.makedirs(output_dir)
			self.stdout.write(self.style.SUCCESS(f"Created directory {output_dir}"))

		# Check if file exists and increment filename if necessary
		base_file_path = os.path.join(output_dir, f"{username}_details.txt")
		output_file_path = base_file_path
		counter = 1
		while os.path.exists(output_file_path):
			output_file_path = os.path.join(output_dir, f"{username}_details_{counter}.txt")
			counter += 1

		# Write output to the file
		with open(output_file_path, 'w') as file:
			file.write(output_content)

		self.stdout.write(self.style.SUCCESS(f"Details saved to {output_file_path}"))

