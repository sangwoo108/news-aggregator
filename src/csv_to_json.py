# Copyright (c) 2023 The Brave Authors. All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://mozilla.org/MPL/2.0/. */

import csv

import orjson
import structlog
from pydantic import ValidationError

from config import get_config
from models.publisher import PublisherModel
from utils import get_cover_infos_lookup, get_favicons_lookup, upload_file

config = get_config()

logger = structlog.getLogger(__name__)

favicons_lookup = get_favicons_lookup()
cover_infos_lookup = get_cover_infos_lookup()

publisher_include_keys = {
    "enabled": True,
    "publisher_name": True,
    "category": True,
    "site_url": True,
    "feed_url": True,
    "favicon_url": True,
    "cover_url": True,
    "background_color": True,
    "score": True,
    "channels": True,
    "rank": True,
    "publisher_id": True,
    "destination_domains": True,
}

feed_include_keys = {
    "category": True,
    "publisher_name": True,
    "content_type": True,
    "publisher_domain": True,
    "publisher_id": True,
    "max_entries": True,
    "og_images": True,
    "creative_instance_id": True,
    "feed_url": True,
    "site_url": True,
    "destination_domains": True,
}


def main():
    publisher_file_path = f"{config.sources_dir / config.sources_file}.csv"
    publisher_output_path = "feed.json"
    publishers = []
    with open(publisher_file_path) as publisher_file_pointer:
        publisher_reader = csv.DictReader(publisher_file_pointer)
        for data in publisher_reader:
            try:
                publisher: PublisherModel = PublisherModel(**data)
                publisher.favicon_url = favicons_lookup.get(publisher.site_url, None)
                cover_info = cover_infos_lookup.get(
                    publisher.site_url, {"cover_url": None, "background_color": None}
                )
                publisher.cover_url = cover_info.get("cover_url")
                publisher.background_color = cover_info.get("background_color")

                publishers.append(publisher)
            except ValidationError as e:
                logger.error(f"{e} on {data}")

    publishers_data_by_url = {
        str(x.feed_url): x.dict(include=feed_include_keys) for x in publishers
    }

    publishers_data_as_list = [
        x.dict(include=publisher_include_keys) for x in publishers
    ]

    publishers_data_as_list = sorted(
        publishers_data_as_list, key=lambda x: x["publisher_name"]
    )

    with open(config.output_path / publisher_output_path, "wb") as f:
        f.write(orjson.dumps(publishers_data_by_url))

    with open(config.output_path / "sources.json", "wb") as f:
        f.write(orjson.dumps(publishers_data_as_list))

    if not config.no_upload:
        upload_file(
            config.output_path / "sources.json",
            config.pub_s3_bucket,
            f"{config.sources_file}.json",
        )
        # Temporarily upload also with incorrect filename as a stopgap for
        # https://github.com/brave/brave-browser/issues/20114
        # Can be removed once fixed in the brave-core client for all Desktop users.
        upload_file(
            config.output_path / "sources.json",
            config.pub_s3_bucket,
            f"{config.sources_file}json",
        )


if __name__ == "__main__":
    main()
