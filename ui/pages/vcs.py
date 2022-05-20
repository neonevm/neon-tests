import typing as tp

from tests.ui.components import extjs
from tests.ui.components import react

from . import BasePage


class VCSPage(BasePage):
    def page_loaded(self):
        self.page.wait_for_selector("text='New VCS Provider'", state="visible", timeout=30000)

    def delete(self) -> "DeleteVCSModal":
        extjs.Button(self.page, icon="x-btn-icon-delete").click()
        return DeleteVCSModal(self.page)

    def clear_search(self):
        self.page.click("div.x-form-filterfield-trigger-cancel-button-default")

    def reauthorize(self):
        extjs.Button(self.page, "Reauthorize on GitHub").click()

    def reload(self):
        extjs.Button(self.page, icon="x-btn-icon-refresh").click()

    def list_vcs(self) -> tp.List[tp.Dict[str, str]]:
        vcses = []
        self.page.wait_for_selector('//div[@class="x-grid-item-container"]/table')
        for el in self.page.query_selector_all('//div[@class="x-grid-item-container"]/table'):
            tds = el.query_selector_all("//td/div")
            vcses.append(
                {
                    "name": tds[0].text_content(),
                    "type": tds[1].text_content(),
                    "usage": tds[2].text_content(),
                }
            )
        return vcses

    def open_new_vcs(self) -> "NewVCSProviderPage":
        extjs.Button(self.page, "New VCS Provider").click()
        return NewVCSProviderPage(self.page)


class DeleteVCSModal(BasePage):
    def page_loaded(self):
        self.page.wait_for_selector(
            '//div[contains(@class, "x-panel")]//div[contains(@class, "icon-delete")]'
        )

    def confirm(self):
        extjs.Button(self.page, text="Delete").click()

    def cancel(self):
        extjs.Button(self.page, text="Cancel").click()


class NewVCSProviderPage(BasePage):
    def page_loaded(self):
        self.page.wait_for_selector("text='New VCS provider'", state="visible", timeout=30000)

    def choose_vcs_provider(self, name: str):
        react.SelectorButton(self.page, name).click()

    def set_provider_name(self, name: str) -> react.Input:
        return react.Input(self.page, title="Enter provider name").fill(name)

    @property
    def callback_url(self) -> str:
        return self.page.inner_text('//h2[text()="Copy callback URL:"]/following-sibling::span')

    def register_vcs(self) -> react.Button:
        return react.Button(self.page, "Register a new OAuth application in GitHub")

    def set_client_id(self, client_id: str) -> react.Input:
        return react.Input(self.page, label="Client ID").fill(client_id)

    def set_client_secret(self, client_secret: str) -> react.Input:
        return react.Input(self.page, label="Client secret").fill(client_secret)

    def cancel_button(self) -> react.Button:
        return react.Button(self.page, "Cancel")

    def create_button(self) -> react.Button:
        return react.Button(self.page, "Create")
