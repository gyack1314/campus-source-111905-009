from tests.support import SourceCase
from playwright.sync_api import sync_playwright
class Contract(SourceCase):
    def setUp(self):
        super().setUp();self.pw=self.stack.enter_context(sync_playwright());self.browser=self.pw.chromium.launch(headless=True,args=["--no-sandbox"]);self.addCleanup(self.browser.close)
        self.page=self.browser.new_page();self.page.goto(self.base+"/portal")
    def hold(self,remove="T1,L1",add="T2,L3"):
        p=self.page;p.get_by_label("换出课程").fill(remove);p.get_by_label("换入课程").fill(add);p.get_by_role("button",name="核对并预占").click()
    def test_actual_portal_catalog(self):
        self.assertEqual(self.page.locator("tr[data-section=LAB-B]").count(),2)
    def test_conflict_preserves_old(self):
        self.hold(add="T2,L2");self.assertIn("时间冲突",self.page.locator("[data-result=rejected]").inner_text())
        self.page.get_by_role("link",name="课表与办理").click();self.assertEqual(self.page.locator("[data-enrolled]").get_attribute("data-enrolled"),"T1,L1,KEEP")
    def test_corequisite_preserves_old(self):
        self.hold(remove="L1",add="L3");self.assertIn("共修",self.page.locator("[data-result=rejected]").inner_text())
    def test_hold_is_not_registration(self):
        self.hold();self.assertEqual(self.source.enrolled,["T1","L1","KEEP"]);self.assertEqual(self.page.locator("[data-hold]").count(),1)
    def test_stale_schedule_rejected(self):
        self.hold();self.control(1);self.page.get_by_role("button",name="确认整组换课").click();self.assertIn("版本变化",self.page.locator("[data-result=stale]").inner_text())
    def test_expiry_not_commit(self):
        self.hold();self.control(2);self.page.get_by_role("button",name="确认整组换课").click();self.assertEqual(self.page.locator("[data-result=expired]").count(),1)
    def test_uncertain_response_has_committed_record(self):
        self.hold();id=self.page.locator("[data-hold]").get_attribute("data-hold");self.page.get_by_role("button",name="确认整组换课").click()
        self.assertEqual(self.page.locator("[data-result=unknown]").count(),1)
        self.page.get_by_role("link",name="办理记录").click();self.assertEqual(self.page.locator("[data-record]").get_attribute("data-record"),id)
        self.page.get_by_role("link",name="课表与办理").click();self.assertEqual(self.page.locator("[data-enrolled]").get_attribute("data-enrolled"),"KEEP,T2,L3")
    def test_capacity_change_rejected(self):
        self.hold();self.control(0,full=True);self.page.get_by_role("button",name="确认整组换课").click()
        self.assertEqual(self.page.locator("[data-result=rejected]").count(),1);self.assertEqual(self.source.enrolled,["T1","L1","KEEP"])
