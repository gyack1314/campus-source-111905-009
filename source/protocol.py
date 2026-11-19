"""本地成组换课门户：业务状态由合成服务端持有。"""
import html
from urllib.parse import parse_qs

CATALOG={
"T1":dict(section="T1",time=9,credits=2,coreq=["L1"]),
"L1":dict(section="L1",time=10,credits=1,coreq=["T1"]),
"KEEP":dict(section="KEEP",time=11,credits=2,coreq=[]),
"T2":dict(section="T2",time=14,credits=2,coreq=["L2","L3"]),
"L2":dict(section="LAB-B",time=11,credits=1,coreq=["T2"]),
"CS-LAB-B":dict(section="LAB-B",time=11,credits=1,coreq=["T2"]),
"L3":dict(section="LAB-C",time=15,credits=1,coreq=["T2"])}
class Source:
    name="实践课程换课门户"
    def __init__(self):
        self.enrolled=["T1","L1","KEEP"];self.version=1;self.holds={};self.records={};self.serial=0;self.external=False
    def page(self,body,status=200):
        return status,{"Content-Type":"text/html; charset=utf-8"},'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>课程办理</title><body><nav><a href="/portal">课表与办理</a> <a href="/records">办理记录</a></nav>'+body+'</body></html>'
    def errors(self,final):
        if len(final)!=len(set(final)):return ["重复课程"]
        if any(x not in CATALOG for x in final):return ["未知挂牌课程"]
        sections=[CATALOG[x]["section"] for x in final]
        errors=[]
        if len(sections)!=len(set(sections)):errors.append("共享班级不能重复注册")
        times=[CATALOG[x]["time"] for x in final]
        if len(times)!=len(set(times)):errors.append("最终课表时间冲突")
        if sum(CATALOG[x]["credits"] for x in final)>6:errors.append("超过六学分上限")
        for x in final:
            required=CATALOG[x]["coreq"]
            if required and not any(y in required or CATALOG[y]["section"] in [CATALOG[r]["section"] for r in required] for y in final if y!=x):
                errors.append(x+"缺少共修课")
        return errors
    def tick(self):
        if self.stage>=1 and not self.external:
            self.version+=1;self.external=True
    def route(self,method,path,q,headers,body):
        self.tick()
        if path in ["/","/portal"]:
            rows="".join(f'<tr data-course="{k}" data-section="{v["section"]}"><td>{k}</td><td>{v["section"]}</td><td>{v["time"]}:00</td><td>{v["credits"]}</td><td>{"/".join(v["coreq"])}</td></tr>' for k,v in CATALOG.items())
            return self.page(f'<h1>合成学生 S1</h1><section data-schedule-version="{self.version}" data-enrolled="{",".join(self.enrolled)}">现有课表：{",".join(self.enrolled)}</section><table><caption>挂牌、共享班级、时段、学分、共修任选一项</caption>{rows}</table><form method="post" action="/hold"><label>换出课程<input name="remove"></label><label>换入课程<input name="add"></label><button>核对并预占</button></form>')
        if path=="/hold" and method=="POST":
            f=parse_qs(body.decode(),keep_blank_values=True)
            remove=[s.strip() for s in f.get("remove",[""])[0].split(",") if s.strip()]
            add=[s.strip() for s in f.get("add",[""])[0].split(",") if s.strip()]
            errors=self.errors([x for x in self.enrolled if x not in remove]+add)
            if any(x not in self.enrolled for x in remove):errors.append("换出课程未注册")
            if self.options.get("full") and any(x in ["L3","L2","CS-LAB-B"] for x in add):errors.append("共享班级名额已满")
            for previous in self.holds.values():
                if previous["status"]=="held" and previous["version"]==self.version and self.stage<previous["expires"]:
                    reserved={CATALOG[x]["section"] for x in previous["add"]}
                    if any(CATALOG[x]["section"] in reserved for x in add if x in CATALOG):errors.append("名额已被其他预占占用")
            if errors:return self.page('<section data-result="rejected">'+html.escape("；".join(errors))+"</section>",409)
            self.serial+=1;id="hold-"+str(self.serial)
            hold=dict(id=id,version=self.version,remove=remove,add=add,expires=self.stage+2,status="held")
            self.holds[id]=hold
            return self.page(f'<section data-hold="{id}" data-version="{self.version}" data-expires-stage="{hold["expires"]}">预占尚未注册；换出{",".join(remove)}；换入{",".join(add)}</section><form method="post" action="/confirm"><input type="hidden" name="hold" value="{id}"><button>确认整组换课</button></form>')
        if path=="/confirm" and method=="POST":
            id=parse_qs(body.decode())["hold"][0];hold=self.holds[id]
            if id in self.records:return self.page('<section data-record="'+id+'">该办理已完成</section>')
            if self.stage>=hold["expires"]:return self.page('<section data-result="expired">预占过期，原课未退</section>',409)
            if hold["version"]!=self.version:return self.page('<section data-result="stale">课表版本变化，原课未退</section>',409)
            final=[x for x in self.enrolled if x not in hold["remove"]]+hold["add"]
            errors=self.errors(final)
            if self.options.get("full"):errors.append("名额变化")
            if errors:return self.page('<section data-result="rejected">'+html.escape("；".join(errors))+"</section>",409)
            self.enrolled=final;self.version+=1;hold["status"]="committed"
            self.records[id]=dict(hold,result_version=self.version,enrolled=list(final))
            if self.options.get("lost_response",True):return self.page('<p data-result="unknown">确认响应中断，请核对办理记录</p>',503)
            return self.page('<section data-record="'+id+'">整组换课已生效</section>')
        if path=="/records":
            rows="".join(f'<article data-record="{id}" data-result-version="{r["result_version"]}" data-state="committed"><p>换出{",".join(r["remove"])}；换入{",".join(r["add"])}</p><p>实际课表：{",".join(r["enrolled"])}</p></article>' for id,r in self.records.items())
            return self.page("<h1>已提交办理</h1>"+(rows or "<p>暂无已提交办理</p>"))
        return self.page("页面不存在",404)
