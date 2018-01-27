from bs4 import BeautifulSoup
import requests, datetime, tqdm, os
from yaml import load
from trello import TrelloClient

def load_config(configfile):

	with open(configfile, 'r') as f:
		config = load(f)
	url = config["url"]
	terms = config["terms"]
	start_date = config["start_date"]
	api_key = config["api_key"]
	api_secret = config["api_secret"]
	oauth_token = config["oauth_token"]
	oauth_secret = config["oauth_secret"]
	board_name = config["board_name"]

	return url, terms, start_date, api_key, api_secret, oauth_token, oauth_secret, board_name

def get_ads_since_date(url, start_date):
	ads = []
	earliest_date = datetime.date.today()
	ad_number = 0

	while earliest_date > start_date:
		print("Searching {}{}".format(url,ad_number))
		response = requests.get("{}{}".format(url,ad_number))
		data = response.text
		soup = BeautifulSoup(data, 'lxml')
		results = soup.find_all('li', {'class':'result-row'})

		for result in results:

			date = datetime.date(*map(int, result.find("time")["datetime"].split(" ")[0].split("-")))
			if date < earliest_date:
				earliest_date = date

			ads.append({"date":date,
						"title":result.find("a", {"class":"result-title"}).text,
						"href":result.find("a", {"class":"result-title"})["href"]})

		ad_number += len(results)

	ads = [ad for ad in ads if ad["date"] >= start_date]
	print("Found {} ads since {}.".format(len(ads), start_date.isoformat()))
	return ads

def search_ads(ads, terms):
	hits = []
	for term in tqdm.tqdm(terms, "Searching through ads..."):
		for i in reversed(range(len(ads))):
			if term in ads[i]["title"].lower():
				hits.append(ads.pop(i))

	print("Found {} hits.".format(len(hits)))
	return hits

def connect_trello(api_key, api_secret, oauth_token, oauth_secret, verbose=False):
	client = TrelloClient(
		api_key=api_key,
		api_secret=api_secret,
		token=oauth_token,
		token_secret=oauth_secret
	)
	if verbose:
		print("Available boards: {}".format(client.list_boards()))

	return client

def get_board_id(client, target_board):
	for board in client.list_boards():
		if board.name.lower() == target_board.lower():
			return board.id
	return ValueError("Board: {} does not exist".format(target_board))

def get_list_id(board, target_list):
	for open_list in board.all_lists():
		if open_list.name.lower() == target_list.lower():
			return open_list.id
	return ValueError("List: {} does not exist".format(target_list))

def add_hit_to_list(hit,trello_unreviewed_list, trello_unreviewed_cards, trello_reviewed_cards):
	if (hit["href"] not in [card.desc for card in trello_reviewed_cards]) and (hit["href"] not in [card.desc for card in trello_unreviewed_cards]):
		trello_unreviewed_list.add_card("{} : {} ".format(hit["date"],hit["title"]),desc=hit["href"])
	return

def update_board(client, hits, target_board=None, unreviewed_list="Unreviewed Ads", reviewed_list="Reviewed Ads"):
	board_id = get_board_id(client, target_board)
	board = client.get_board(board_id=board_id)
	trello_unreviewed_list = board.get_list(get_list_id(board, unreviewed_list))
	trello_unreviewed_cards = trello_unreviewed_list.list_cards()

	trello_reviewed_list = board.get_list(get_list_id(board, reviewed_list))
	trello_reviewed_cards = trello_reviewed_list.list_cards()

	for hit in tqdm.tqdm(hits, desc="Updating Trello board..."):
		add_hit_to_list(hit, trello_unreviewed_list, trello_unreviewed_cards, trello_reviewed_cards)

	return

if __name__ == "__main__":
	base = os.path.realpath(__file__)
	config_files = [os.path.join(base,fname) for fname in ["config.yaml", "config2.yaml"]]
	for fname in config_files:
		url, terms, start_date, api_key, api_secret, oauth_token, oauth_secret, board_name = load_config(fname)
		client = connect_trello(api_key=api_key, api_secret=api_secret, oauth_token=oauth_token, oauth_secret=oauth_secret)
		ads = get_ads_since_date(url, start_date)
		hits = search_ads(ads, terms)
		update_board(client, hits, target_board=board_name)
	print("Trello has been updated.")