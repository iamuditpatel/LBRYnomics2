import config
import datetime
import json
import numpy as np
import pandas as pd
import requests
import sqlite3
import time
import yaml





def subscriber_counts(num=200, preview=False):
    """
    Get subscriber counts for all channels.
    """
    now = time.time()

    # Open previous JSON
    f = open("json/subscriber_counts.json")
    old = json.load(f)
    f.close()

    # Get auth token
    f= open("secrets.yaml")
    auth_token = yaml.load(f, Loader=yaml.SafeLoader)["auth_token"]
    f.close()

    # Create a dict from the old JSON, where the claim_id can return
    # the subscribers and the rank
    old_dict = {}
    for i in range(len(old["ranks"])):
        old_dict[old["claim_ids"][i]] = (old["subscribers"][i], old["ranks"][i])

    # Open claims.db
    conn = sqlite3.connect(config.claims_db_file)
    c = conn.cursor()
    query = "select claim_name, claim_id, claim_hash from claim where claim_type = 2;"
    vanity_names = []
    claim_ids = []
    subscribers = []

    # Iterate over query results
    i = 0
    for row in c.execute(query):
        vanity_names.append(row[0])
        claim_ids.append(row[1])
        i = i + 1

    vanity_names = np.array(vanity_names)
    claim_ids = np.array(claim_ids)

    # Now get number of claims in each channel
    query = \
"""
select c2.claim_id claim_ids, count(*) num_claims
    from claim c1 inner join claim c2 on c2.claim_hash = c1.channel_hash
    group by c2.claim_hash
    having num_claims > 0;
"""

    claims_with_content = {}
    k = 0
    for row in c.execute(query):
        claims_with_content[row[0]] = None
        k += 1
        print("Getting channels with content...found {k} so far.".format(k=k))

    start = time.time()

    # DMCA'd channels + rewards scammers
    black_list = {  "d5557f4c61d6725f1a51141bbee43cdd2576e415": None,
                    "35100b76e32aeb2764d334186249fa1b90d6cd74": None,
                    "f2fe17fb1c62c22f8319c38d0018726928454112": None,
                    "17db8343914760ba509ed1f8c8e34dcc588614b7": None,
                    "06a31b83cd38723527861a1ca5349b0187f92193": None,
                    "9b7a749276c69f39a2d2d76ca4353c0d8f75217d": None,
                    "b1fa196661570de64ff92d031116a2985af6034c": None,
                    "4e5e34d0ab3cae6f379dad75afadb0c1f683d30f": None,
                    "86612188eea0bda3efc6d550a7ad9c96079facff": None,
                    "00aa9655c127cccb2602d069e1982e08e9f96636": None,
                    "4f2dba9827ae28a974fbc78f1b12e67b8e0a32c9": None,
                    "c133c44e9c6ee71177f571646d5b0000489e419f": None,
                    "eeb3c6452b240a9f6a17c06887547be54a90a4b9": None,
                    "f625ef83a3f34cac61b6b3bdef42be664fd827da": None,
                    "ed77d38da413377b8b3ee752675662369b7e0a49": None,
                    "481c95bd9865dc17770c277ae50f0cc306dfa8af": None,
                    "3c5aa133095f97bb44f13de7c85a2a4dd5b4fcbe": None,
                    "bd6abead1787fa94722bd7d064f847de76de5655": None,
                    "6114b2ce20b55c40506d4bd3f7d8f917b1c37a75": None,
                    "0c65674e28f2be555570c5a3be0c3ce2eda359d1": None,
                    "3395d03f379888ffa789f1fa45d6619c2037e3de": None,
                    "cd31c9ddea4ac4574df50a1f84ee86aa17910ea2": None,
                    "9d48c8ab0ad53c392d4d6052daf5f8a8e6b5a185": None,
                    "51fbdb73893c1b04a7d4c4465ffcd1138abc9e93": None,
                    "5183307ce562dad27367bdf94cdafde38756dca7": None,
                    "56dca125e775b2fe607d3d8d6c29e7ecfa3cbd96": None,
                    "a58926cb716c954bdab0187b455a63a2c592310e": None,
                    "aa83130864bf22c66934c1af36182c91219233aa": None,
                    "f3c1fda9bf1f54710b62ffe4b14be6990288d9ff": None,
                    "6291b3b53dde4160ce89067281300585bdf51905": None,
                    "eeef31480a14684a95898ecd3bcf3a5569e41a28": None,
                    "8b8b3c8cd3e8364c37067b80bd5a20c09a0a0094": None,
                    "725189cd101ff372edbce1c05ef04346864d3254": None,
                    "35100b76e32aeb2764d334186249fa1b90d6cd74": None,
                    "47beabb163e02e10f99838ffc10ebc57f3f13938": None,
                    "e0bb55d4d6aec9886858df8f1289974e673309c7": None }

    include = np.zeros(len(claim_ids), dtype=bool)
    for i in range(len(claim_ids)):
        include[i] = (claim_ids[i] in claims_with_content) and \
                            claim_ids[i] not in black_list

    vanity_names = vanity_names[include]
    claim_ids = claim_ids[include]

    k = 0
    while True:
        """
        Go in batches of 100 with a pause in between
        """
        time.sleep(3.0)

        # Cover a certain range of channels
        start = 100*k
        end = 100*(k+1)
        final = end >= len(claim_ids)
        if final:
            end = len(claim_ids)

        
        # Attempt the request until it succeeds
        while True:

            # Prepare the request to the LBRY API
            url = "https://api.lbry.com/subscription/sub_count?auth_token=" +\
                        auth_token + "&claim_id="
            for i in range(start, end):
                url += claim_ids[i] + ","
            url = url[0:-1] # No final comma

            f = open("url.txt", "w")
            f.write(url)
            f.close()

            try:
                # Do the request
                result = requests.get(url)
                result = result.json()
                break
            except:
                time.sleep(3.0)
                pass

        # Get sub counts from the result and put them in the subscribers list
        for x in result["data"]:
            subscribers.append(x)
            i = len(subscribers)-1

        print("Processed {end} channels.".format(end=end))
        if final:
            break
        k += 1

    # Sort by number of subscribers then by vanity name.
    # Zip subs with name
    s_n = []
    indices = []
    for i in range(len(vanity_names)):
        s_n.append((subscribers[i], vanity_names[i]))
        indices.append(i)
    indices = sorted(indices, key=lambda x: (s_n[x][0], s_n[x][1]))[::-1]

    vanity_names = np.array(vanity_names)[indices]
    claim_ids = np.array(claim_ids)[indices]
    subscribers = np.array(subscribers)[indices]

    # Put the top 100 into the dict
    my_dict = {}
    my_dict["unix_time"] = now
    my_dict["human_time_utc"] = str(datetime.datetime.utcfromtimestamp(int(now))) + " UTC"
    my_dict["old_unix_time"] = old["unix_time"]
    my_dict["old_human_time_utc"] = old["human_time_utc"]
    my_dict["interval_days"] = np.round((my_dict["unix_time"]\
                                        - my_dict["old_unix_time"])/86400.0, 2)
    my_dict["ranks"] = []
    my_dict["vanity_names"] = []
    my_dict["claim_ids"] = []
    my_dict["subscribers"] = []
    my_dict["change"] = []
    my_dict["rank_change"] = []
    my_dict["is_nsfw"] = []

    grey_list = ["f24ab6f03d96aada87d4e14b2dac4aa1cee8d787",
                 "fd4b56c7216c2f96db4b751af68aa2789c327d48"]

    for i in range(num):
        my_dict["ranks"].append(i+1)
        my_dict["vanity_names"].append(vanity_names[i])
        my_dict["claim_ids"].append(claim_ids[i])
        my_dict["subscribers"].append(int(subscribers[i]))
        my_dict["is_nsfw"].append(False)

        # Compute subscribers change
        my_dict["change"].append(None)
        my_dict["rank_change"].append(None)
        try:
            my_dict["change"][-1] = int(subscribers[i]) - \
                                        old_dict[claim_ids[i]][0]
            my_dict["rank_change"][-1] = old_dict[claim_ids[i]][1] - \
                                            int(my_dict["ranks"][-1])
        except:
            pass

        # Mark some channels NSFW manually
        if my_dict["claim_ids"][-1] in grey_list:
            my_dict["is_nsfw"][-1] = True
        else:         
            # Do SQL queries to see if there's a mature tag
            query = "SELECT tag.tag FROM claim INNER JOIN tag ON tag.claim_hash = claim.claim_hash WHERE claim_id = '"
            query += claim_ids[i] + "';"

            for row in c.execute(query):
                if row[0].lower() == "mature":
                    my_dict["is_nsfw"][-1] = True

    if preview:
        f = open("json/subscriber_counts_preview.csv", "w")
        # Create data frame and make CSV
        df = pd.DataFrame()
        df["ranks"] = my_dict["ranks"]
        df["vanity_names"] = my_dict["vanity_names"]
        df["claim_ids"] = my_dict["claim_ids"]
        df["is_nsfw"] = my_dict["is_nsfw"]
        df["followers"] = my_dict["subscribers"]
        df["change"] = my_dict["change"]
        df["rank_change"] = my_dict["rank_change"]
        df.to_csv("json/subscriber_counts_preview.csv")


    else:
        f = open("json/subscriber_counts.json", "w")
        import update_rss
        update_rss.update(my_dict["human_time_utc"])
        f.write(json.dumps(my_dict, indent=4))
        f.close()

    conn.close()

# Main loop
if __name__ == "__main__":

    # Needs an initial JSON file to bootstrap from
    hour = 3600.0
    day = 24*hour
    week = 7*day


    f = open("json/subscriber_counts.json")
    t = json.load(f)["unix_time"]
    f.close()


    # Update frequency
    interval = 0.5*week


    while True:
        gap = time.time() - t

        msg = "{d} days until next update.".format(d=(interval - gap)/day)
        print(msg + "        ", end="\r", flush=True)
        time.sleep(1.0 - time.time()%1)

        if gap >= interval:
            subscriber_counts()

            f = open("json/subscriber_counts.json")
            t = json.load(f)["unix_time"]
            f.close()


