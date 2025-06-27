from typing import Literal

import pydantic
from slack_sdk.models.blocks import (
    Block,
    SectionBlock,
    DividerBlock,
    PlainTextObject,
    OverflowMenuElement,
    Option,
    ButtonElement,
)


class SlackNotification(pydantic.BaseModel):
    blocks: list[dict] = []

    def add_block(self, block: Block):
        self.blocks.append(block.to_dict())

    def add_combined_block(
        self,
        build_info: dict,
        network: str,
        failed_tests: str,
        report_urls: list[dict[Literal["name", "url"], str]],
        comments: list[str],
    ):
        # Create first 2 columns
        fields = [
            {"text": "*Failed build*", "type": "mrkdwn"},
            {"text": f"<{build_info['url']}|`{build_info['id']}`>", "type": "mrkdwn"},
            {"text": "*Network*", "type": "mrkdwn"},
            {"text": network, "type": "mrkdwn"},
        ]

        if failed_tests:
            fields.extend([{"text": "*Failed Tests*", "type": "mrkdwn"}, {"text": failed_tests, "type": "mrkdwn"}])

        for index, comment in enumerate(comments):
            if comment:
                number = f" {index + 1}" if len(comments) > 1 else ""
                fields.extend([{"text": f"*Comment{number}*", "type": "mrkdwn"}, {"text": comment, "type": "mrkdwn"}])

        # Create accessory (third column)
        if report_urls:
            if len(report_urls) > 1:
                # Overflow menu with multiple links
                options = []

                for report_url in report_urls:
                    text = "VIEW REPORT" if len(report_urls) <= 1 else f"VIEW REPORT: {report_url['name']}"
                    option = Option(value=report_url["name"], text=PlainTextObject(text=text), url=report_url["url"])
                    options.append(option)

                accessory = OverflowMenuElement(options=options)
            else:
                # Single button
                accessory = ButtonElement(text=PlainTextObject(text="VIEW REPORT"), url=report_urls[0]["url"])
        else:
            accessory = None

        section_block = SectionBlock(fields=fields, accessory=accessory)
        self.add_block(section_block)

    def add_divider(self):
        block = DividerBlock()
        self.add_block(block)
