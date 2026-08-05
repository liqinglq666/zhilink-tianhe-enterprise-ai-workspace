# -*- coding: utf-8 -*-
"""Persistent, organization-scoped enterprise-service workflows."""
from __future__ import annotations

import hashlib, json, re
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4
from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column
from .auth_store import AccountStoreError, OrganizationMembershipRecord, OrganizationProjectRecord, UserRecord, get_account_store
from .knowledge_store import KnowledgeArticleRecord, KnowledgeVersionRecord
from .project_store import Base, ProjectRecord
from .service_workflow_schemas import WorkflowCreateRequest

EDITORS={"owner","admin","editor"}; REVIEWERS={"owner","admin"}; ASSIGNEES=EDITORS
POL=re.compile(r"\bPOL-\d{3}\b"); KB=re.compile(r"^THKB-([A-F0-9]{8})@v(\d+)$"); URL=re.compile(r"\((https://[^\s)]+)\)")
DEFAULT_NODES=(
("intake","接收建档","核对企业身份、联系人、服务目标和当前项目材料。"),
("diagnosis","需求诊断","梳理企业需求、约束、优先级和仍需补充的信息。"),
("evidence","资料与依据核验","核对项目模块、人工审核状态、官方政策引用和组织知识引用。"),
("plan","服务方案","形成可执行方案、责任分工、时间节点和风险处理方式。"),
("delivery","执行跟进","记录服务动作、企业反馈、阻塞事项和阶段交付。"),
("closeout","结项审核","汇总结论、未决事项、后续责任和结项依据。"),)

class ServiceCaseRecord(Base):
    __tablename__="service_cases"; __table_args__=(UniqueConstraint("organization_id","case_number",name="uq_service_case_number"),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True); organization_id:Mapped[str]=mapped_column(String(36),ForeignKey("organizations.id",ondelete="CASCADE"),index=True); project_id:Mapped[str]=mapped_column(String(36),ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    case_number:Mapped[str]=mapped_column(String(13)); title:Mapped[str]=mapped_column(String(200)); objective:Mapped[str]=mapped_column(Text); priority:Mapped[str]=mapped_column(String(20),default="normal",index=True); status:Mapped[str]=mapped_column(String(30),default="draft",index=True)
    owner_user_id:Mapped[str]=mapped_column(String(36),ForeignKey("users.id",ondelete="RESTRICT")); due_date:Mapped[date|None]=mapped_column(Date); lock_version:Mapped[int]=mapped_column(Integer,default=1); current_context_version:Mapped[int]=mapped_column(Integer,default=1); closure_summary:Mapped[str]=mapped_column(Text,default="")
    created_by_user_id:Mapped[str]=mapped_column(String(36),ForeignKey("users.id",ondelete="RESTRICT")); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc)); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),onupdate=lambda:datetime.now(timezone.utc)); completed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))

class ServiceCaseNodeRecord(Base):
    __tablename__="service_case_nodes"; __table_args__=(UniqueConstraint("case_id","sequence",name="uq_service_case_node_sequence"),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True); case_id:Mapped[str]=mapped_column(String(36),ForeignKey("service_cases.id",ondelete="CASCADE"),index=True); sequence:Mapped[int]=mapped_column(Integer); node_type:Mapped[str]=mapped_column(String(30)); title:Mapped[str]=mapped_column(String(120)); description:Mapped[str]=mapped_column(Text); status:Mapped[str]=mapped_column(String(30),default="pending",index=True)
    assignee_user_id:Mapped[str|None]=mapped_column(String(36),ForeignKey("users.id",ondelete="SET NULL")); due_date:Mapped[date|None]=mapped_column(Date); output_summary:Mapped[str]=mapped_column(Text,default=""); decision_note:Mapped[str]=mapped_column(Text,default=""); started_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); submitted_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); completed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),onupdate=lambda:datetime.now(timezone.utc))

class ServiceCaseContextRecord(Base):
    __tablename__="service_case_contexts"; __table_args__=(UniqueConstraint("case_id","context_version",name="uq_service_case_context_version"),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True); case_id:Mapped[str]=mapped_column(String(36),ForeignKey("service_cases.id",ondelete="CASCADE"),index=True); context_version:Mapped[int]=mapped_column(Integer); project_id:Mapped[str]=mapped_column(String(36)); project_name:Mapped[str]=mapped_column(String(120)); project_version:Mapped[int]=mapped_column(Integer); project_updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True)); snapshot:Mapped[dict[str,Any]]=mapped_column(JSON); context_sha256:Mapped[str]=mapped_column(String(64)); created_by_user_id:Mapped[str]=mapped_column(String(36),ForeignKey("users.id",ondelete="RESTRICT")); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class ServiceCaseEventRecord(Base):
    __tablename__="service_case_events"
    id:Mapped[str]=mapped_column(String(36),primary_key=True); case_id:Mapped[str]=mapped_column(String(36),ForeignKey("service_cases.id",ondelete="CASCADE"),index=True); node_id:Mapped[str|None]=mapped_column(String(36),ForeignKey("service_case_nodes.id",ondelete="CASCADE")); action:Mapped[str]=mapped_column(String(40)); before_status:Mapped[str]=mapped_column(String(30)); after_status:Mapped[str]=mapped_column(String(30)); actor_user_id:Mapped[str]=mapped_column(String(36),ForeignKey("users.id",ondelete="RESTRICT")); actor_name:Mapped[str]=mapped_column(String(120)); actor_role:Mapped[str]=mapped_column(String(20)); note:Mapped[str]=mapped_column(Text,default=""); payload_sha256:Mapped[str]=mapped_column(String(64)); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

def now(): return datetime.now(timezone.utc)
def digest(v): return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
def clean(s,n=500): return " ".join(re.sub(r"^[\s>*#\-+\d.\[\]xX]+","",s or "").split())[:n]
def official(md):
    out={}
    for line in (md or "").splitlines():
        ids=POL.findall(line)
        if not ids: continue
        cells=[x.strip() for x in line.strip().strip("|").split("|")]; m=URL.search(line)
        for cid in ids:
            item=out.setdefault(cid,{"citation_id":cid,"title":"","official_url":""})
            if len(cells)>1 and cid in cells[0]: item["title"]=clean(cells[1])
            if m: item["official_url"]=m.group(1)[:2000]
    return [out[k] for k in sorted(out)][:20]
def pending(results):
    out=[]; seen=set()
    for module,content in results.items():
        active=False
        for raw in (content or "").splitlines():
            s=raw.strip()
            if s.startswith("#"): active="待确认" in s or "未决" in s; continue
            if not ((active and s.startswith(("-","*","+","1.","2.","3.","["))) or "待确认" in s): continue
            text=clean(s,300); key=(module,text)
            if text and text not in {"待确认","待确认信息"} and key not in seen: seen.add(key); out.append({"module":module,"text":text})
            if len(out)>=40:return out
    return out

class ServiceWorkflowStore:
    def __init__(self):
        try:
            a=get_account_store(); self.sessions=a.sessions; self.engine=a.projects.engine; Base.metadata.create_all(self.engine)
        except (SQLAlchemyError,AccountStoreError) as e: raise AccountStoreError(503,"WORKFLOW_STORAGE_UNAVAILABLE","企业服务流程存储暂时不可用。",retryable=True) from e
    def case(self,s,org,cid,lock=False):
        q=select(ServiceCaseRecord).where(ServiceCaseRecord.id==cid,ServiceCaseRecord.organization_id==org)
        r=s.scalar(q.with_for_update() if lock else q)
        if not r: raise AccountStoreError(404,"WORKFLOW_NOT_FOUND","企业服务流程不存在或无权访问。")
        return r
    def node(self,s,cid,nid,lock=False):
        q=select(ServiceCaseNodeRecord).where(ServiceCaseNodeRecord.id==nid,ServiceCaseNodeRecord.case_id==cid); r=s.scalar(q.with_for_update() if lock else q)
        if not r: raise AccountStoreError(404,"WORKFLOW_NODE_NOT_FOUND","流程节点不存在。")
        return r
    def project(self,s,org,pid):
        r=s.scalar(select(ProjectRecord).join(OrganizationProjectRecord,OrganizationProjectRecord.project_id==ProjectRecord.id).where(ProjectRecord.id==pid,OrganizationProjectRecord.organization_id==org))
        if not r: raise AccountStoreError(404,"WORKFLOW_PROJECT_NOT_FOUND","项目不存在、未迁移到当前组织或无权访问。")
        return r
    def member(self,s,org,uid,assign=False):
        row=s.execute(select(UserRecord,OrganizationMembershipRecord).join(OrganizationMembershipRecord,OrganizationMembershipRecord.user_id==UserRecord.id).where(OrganizationMembershipRecord.organization_id==org,OrganizationMembershipRecord.user_id==uid,OrganizationMembershipRecord.status=="active")).first()
        if not row or (assign and row[1].role not in ASSIGNEES): raise AccountStoreError(422,"WORKFLOW_ASSIGNEE_INVALID","负责人不是当前组织可处理流程的有效成员。")
        return row
    def kbrefs(self,s,org,citations):
        out=[]; today=date.today()
        for c in citations:
            m=KB.fullmatch(c)
            if not m: raise AccountStoreError(422,"WORKFLOW_KNOWLEDGE_CITATION_INVALID",f"知识引用格式无效：{c}")
            code=f"THKB-{m.group(1)}"; ver=int(m.group(2)); a=s.scalar(select(KnowledgeArticleRecord).where(KnowledgeArticleRecord.organization_id==org,KnowledgeArticleRecord.citation_code==code,KnowledgeArticleRecord.lifecycle_status=="active"))
            if not a or a.published_version!=ver: raise AccountStoreError(422,"WORKFLOW_KNOWLEDGE_CITATION_UNPUBLISHED",f"知识引用不是当前组织的已发布版本：{c}")
            v=s.scalar(select(KnowledgeVersionRecord).where(KnowledgeVersionRecord.article_id==a.id,KnowledgeVersionRecord.version_number==ver))
            if not v or (v.valid_from and v.valid_from>today) or (v.valid_until and v.valid_until<today): raise AccountStoreError(422,"WORKFLOW_KNOWLEDGE_CITATION_EXPIRED",f"知识引用尚未生效或已经失效：{c}")
            src=dict(v.source or {}); out.append({"citation_id":c,"title":v.title,"category":v.category,"source_type":str(src.get("source_type") or ""),"issuer":str(src.get("issuer") or src.get("title") or ""),"valid_until":v.valid_until.isoformat() if v.valid_until else None,"content_sha256":v.content_sha256})
        return out
    def snapshot(self,s,org,p,citations):
        snap=dict(p.snapshot or {}); results=dict(snap.get("results") or {}); reviews=dict(snap.get("reviews") or {}); modules=[]
        for mod,content in results.items():
            if not content: continue
            rv=dict(reviews.get(mod) or {}); modules.append({"module":mod,"result_sha256":hashlib.sha256(content.encode()).hexdigest(),"excerpt":" ".join(content.split())[:500],"review_status":str(rv.get("status") or "unreviewed"),"reviewed_by":str(rv.get("reviewed_by_name") or ""),"reviewed_at":str(rv.get("reviewed_at") or "")})
        ctx={"profile":dict(snap.get("profile") or {}),"identity":dict(snap.get("identity") or {}),"modules":modules[:12],"official_policy_references":official(results.get("policy","")),"knowledge_references":self.kbrefs(s,org,citations),"pending_items":pending(results)}
        return ctx,digest(ctx)
    def add_context(self,s,c,p,uid,citations):
        snap,h=self.snapshot(s,c.organization_id,p,citations); cur=s.scalar(select(ServiceCaseContextRecord).where(ServiceCaseContextRecord.case_id==c.id,ServiceCaseContextRecord.context_version==c.current_context_version))
        if cur and cur.context_sha256==h and cur.project_version==p.lock_version:return cur
        ver=1 if not cur else c.current_context_version+1; x=ServiceCaseContextRecord(id=str(uuid4()),case_id=c.id,context_version=ver,project_id=p.id,project_name=p.name,project_version=p.lock_version,project_updated_at=p.updated_at,snapshot=snap,context_sha256=h,created_by_user_id=uid); s.add(x); c.current_context_version=ver; return x
    def event(self,s,c,node,action,before,after,uid,name,role,note,payload): s.add(ServiceCaseEventRecord(id=str(uuid4()),case_id=c.id,node_id=node.id if node else None,action=action,before_status=before,after_status=after,actor_user_id=uid,actor_name=name[:120],actor_role=role,note=(note or "")[:3000],payload_sha256=digest(payload)))
    def check(self,c,v):
        if c.lock_version!=v: raise AccountStoreError(409,"WORKFLOW_VERSION_CONFLICT",f"流程已更新到 v{c.lock_version}，请重新载入后操作。")
    def create(self,*,organization_id,actor_user_id,actor_name,actor_role,payload:WorkflowCreateRequest):
        if actor_role not in EDITORS: raise AccountStoreError(403,"WORKFLOW_FORBIDDEN","当前角色不能创建企业服务流程。")
        try:
            with self.sessions.begin() as s:
                p=self.project(s,organization_id,payload.project_id); owner=payload.owner_user_id or actor_user_id; self.member(s,organization_id,owner,True)
                c=ServiceCaseRecord(id=str(uuid4()),organization_id=organization_id,project_id=p.id,case_number=f"THSC-{uuid4().hex[:8].upper()}",title=payload.title,objective=payload.objective,priority=payload.priority,owner_user_id=owner,due_date=payload.due_date,created_by_user_id=actor_user_id); s.add(c); s.flush()
                for i,(typ,title,desc) in enumerate(DEFAULT_NODES,1): s.add(ServiceCaseNodeRecord(id=str(uuid4()),case_id=c.id,sequence=i,node_type=typ,title=title,description=desc,assignee_user_id=owner))
                self.add_context(s,c,p,actor_user_id,payload.knowledge_citations); self.event(s,c,None,"create","none","draft",actor_user_id,actor_name,actor_role,"创建企业服务流程",{"project_id":p.id,"knowledge_citations":payload.knowledge_citations}); s.flush()
            return self.get(organization_id=organization_id,case_id=c.id)
        except AccountStoreError: raise
        except SQLAlchemyError as e: raise AccountStoreError(503,"WORKFLOW_STORAGE_UNAVAILABLE","企业服务流程创建失败。",retryable=True) from e
    def list(self,*,organization_id,limit,offset,status):
        with self.sessions() as s:
            q=select(ServiceCaseRecord).where(ServiceCaseRecord.organization_id==organization_id)
            if status:q=q.where(ServiceCaseRecord.status==status)
            total=int(s.scalar(select(func.count()).select_from(q.subquery())) or 0); rows=s.scalars(q.order_by(ServiceCaseRecord.updated_at.desc()).limit(limit).offset(offset)).all(); return [self.case_dict(s,r,False) for r in rows],total
    def get(self,*,organization_id,case_id):
        with self.sessions() as s:return self.case_dict(s,self.case(s,organization_id,case_id),True)
    def case_dict(self,s,c,detail):
        owner=s.get(UserRecord,c.owner_user_id); nodes=s.scalars(select(ServiceCaseNodeRecord).where(ServiceCaseNodeRecord.case_id==c.id).order_by(ServiceCaseNodeRecord.sequence)).all(); d={"id":c.id,"organization_id":c.organization_id,"project_id":c.project_id,"case_number":c.case_number,"title":c.title,"objective":c.objective,"priority":c.priority,"status":c.status,"owner_user_id":c.owner_user_id,"owner_name":owner.display_name if owner else "","due_date":c.due_date,"lock_version":c.lock_version,"current_context_version":c.current_context_version,"completed_nodes":sum(n.status in {"completed","skipped"} for n in nodes),"total_nodes":len(nodes),"created_at":c.created_at,"updated_at":c.updated_at,"completed_at":c.completed_at}
        if not detail:return d
        x=s.scalar(select(ServiceCaseContextRecord).where(ServiceCaseContextRecord.case_id==c.id,ServiceCaseContextRecord.context_version==c.current_context_version)); d.update({"closure_summary":c.closure_summary,"nodes":[self.node_dict(s,n) for n in nodes],"context":self.context_dict(x)}); return d
    def node_dict(self,s,n):
        u=s.get(UserRecord,n.assignee_user_id) if n.assignee_user_id else None; return {"id":n.id,"case_id":n.case_id,"sequence":n.sequence,"node_type":n.node_type,"title":n.title,"description":n.description,"status":n.status,"assignee_user_id":n.assignee_user_id,"assignee_name":u.display_name if u else "","due_date":n.due_date,"output_summary":n.output_summary,"decision_note":n.decision_note,"started_at":n.started_at,"submitted_at":n.submitted_at,"completed_at":n.completed_at,"updated_at":n.updated_at}
    def context_dict(self,x):
        snap=dict(x.snapshot or {}); return {"context_version":x.context_version,"project_id":x.project_id,"project_name":x.project_name,"project_version":x.project_version,"project_updated_at":x.project_updated_at,"profile":snap.get("profile") or {},"identity":snap.get("identity") or {},"modules":snap.get("modules") or [],"official_policy_references":snap.get("official_policy_references") or [],"knowledge_references":snap.get("knowledge_references") or [],"pending_items":snap.get("pending_items") or [],"context_sha256":x.context_sha256,"created_by_user_id":x.created_by_user_id,"created_at":x.created_at}
    def update(self,*,organization_id,case_id,actor_user_id,actor_name,actor_role,lock_version,title,objective,priority,owner_user_id,due_date,clear_due_date):
        if actor_role not in EDITORS: raise AccountStoreError(403,"WORKFLOW_FORBIDDEN","当前角色不能修改企业服务流程。")
        with self.sessions.begin() as s:
            c=self.case(s,organization_id,case_id,True); self.check(c,lock_version); before=c.status
            if title is not None:c.title=title
            if objective is not None:c.objective=objective
            if priority is not None:c.priority=priority
            if owner_user_id is not None:
                if actor_role not in REVIEWERS and owner_user_id!=actor_user_id: raise AccountStoreError(403,"WORKFLOW_FORBIDDEN","编辑者只能把自己设为流程负责人。")
                self.member(s,organization_id,owner_user_id,True); c.owner_user_id=owner_user_id
            if due_date is not None:c.due_date=due_date
            elif clear_due_date:c.due_date=None
            c.lock_version+=1;c.updated_at=now();self.event(s,c,None,"update",before,c.status,actor_user_id,actor_name,actor_role,"更新流程信息",{"owner":owner_user_id,"due":due_date})
        return self.get(organization_id=organization_id,case_id=case_id)
    def refresh_context(self,*,organization_id,case_id,actor_user_id,actor_name,actor_role,lock_version,citations,note):
        if actor_role not in EDITORS: raise AccountStoreError(403,"WORKFLOW_FORBIDDEN","当前角色不能刷新流程依据。")
        with self.sessions.begin() as s:
            c=self.case(s,organization_id,case_id,True);self.check(c,lock_version);p=self.project(s,organization_id,c.project_id);old=c.current_context_version;x=self.add_context(s,c,p,actor_user_id,citations)
            if x.context_version!=old:c.lock_version+=1;c.updated_at=now();self.event(s,c,None,"refresh_context",str(old),str(x.context_version),actor_user_id,actor_name,actor_role,note or "刷新办理依据",{"project_version":p.lock_version,"knowledge_citations":citations})
        return self.get(organization_id=organization_id,case_id=case_id)
    def update_node(self,*,organization_id,case_id,node_id,actor_user_id,actor_name,actor_role,lock_version,assignee_user_id,due_date,clear_due_date,description):
        if actor_role not in REVIEWERS: raise AccountStoreError(403,"WORKFLOW_FORBIDDEN","只有管理员或所有者可以调整节点责任。")
        with self.sessions.begin() as s:
            c=self.case(s,organization_id,case_id,True);self.check(c,lock_version);n=self.node(s,c.id,node_id,True);before=n.status
            if assignee_user_id is not None:self.member(s,organization_id,assignee_user_id,True);n.assignee_user_id=assignee_user_id
            if due_date is not None:n.due_date=due_date
            elif clear_due_date:n.due_date=None
            if description is not None:n.description=description
            n.updated_at=now();c.lock_version+=1;c.updated_at=now();self.event(s,c,n,"update_node",before,n.status,actor_user_id,actor_name,actor_role,"调整节点责任或期限",{"assignee":assignee_user_id,"due":due_date})
        return self.get(organization_id=organization_id,case_id=case_id)
    def node_action(self,*,organization_id,case_id,node_id,actor_user_id,actor_name,actor_role,action,lock_version,note,output_summary):
        if actor_role not in EDITORS: raise AccountStoreError(403,"WORKFLOW_FORBIDDEN","当前角色不能处理流程节点。")
        with self.sessions.begin() as s:
            c=self.case(s,organization_id,case_id,True);self.check(c,lock_version)
            if c.status in {"completed","cancelled"}: raise AccountStoreError(409,"WORKFLOW_ACTION_INVALID","已结项或已取消的流程不能继续处理节点。")
            n=self.node(s,c.id,node_id,True)
            if actor_role not in REVIEWERS:
                if n.assignee_user_id and n.assignee_user_id!=actor_user_id: raise AccountStoreError(403,"WORKFLOW_NODE_ASSIGNEE_REQUIRED","该节点已分配给其他处理人。")
                if not n.assignee_user_id:n.assignee_user_id=actor_user_id
            before=n.status
            if action=="start" and n.status=="pending":n.status="in_progress";n.started_at=n.started_at or now();c.status="active" if c.status=="draft" else c.status
            elif action=="block" and n.status=="in_progress":n.status="blocked";n.decision_note=note
            elif action=="resume" and n.status=="blocked":n.status="in_progress";n.decision_note=note
            elif action=="submit" and n.status in {"in_progress","blocked"}:n.status="pending_review";n.output_summary=output_summary;n.submitted_at=now();n.decision_note=note
            elif action=="approve" and n.status=="pending_review" and actor_role in REVIEWERS:n.status="completed";n.completed_at=now();n.decision_note=note
            elif action=="return" and n.status=="pending_review" and actor_role in REVIEWERS:n.status="in_progress";n.decision_note=note
            elif action=="skip" and n.status not in {"completed","skipped"} and actor_role in REVIEWERS:n.status="skipped";n.completed_at=now();n.decision_note=note
            elif action=="reopen" and n.status in {"completed","skipped"} and actor_role in REVIEWERS:n.status="in_progress";n.completed_at=None;n.decision_note=note;c.status="active" if c.status=="pending_review" else c.status
            elif action in {"approve","return","skip","reopen"} and actor_role not in REVIEWERS: raise AccountStoreError(403,"WORKFLOW_FORBIDDEN","只有管理员或所有者可以审核节点。")
            else: raise AccountStoreError(409,"WORKFLOW_NODE_ACTION_INVALID","当前节点状态不能执行该操作。")
            n.updated_at=now();c.lock_version+=1;c.updated_at=now();self.event(s,c,n,action,before,n.status,actor_user_id,actor_name,actor_role,note,{"output_summary":output_summary,"assignee":n.assignee_user_id})
        return self.get(organization_id=organization_id,case_id=case_id)
    def case_action(self,*,organization_id,case_id,actor_user_id,actor_name,actor_role,action,lock_version,note,acknowledge_open_items):
        if actor_role not in EDITORS: raise AccountStoreError(403,"WORKFLOW_FORBIDDEN","当前角色不能操作企业服务流程。")
        with self.sessions.begin() as s:
            c=self.case(s,organization_id,case_id,True);self.check(c,lock_version);before=c.status;nodes=s.scalars(select(ServiceCaseNodeRecord).where(ServiceCaseNodeRecord.case_id==c.id)).all();x=s.scalar(select(ServiceCaseContextRecord).where(ServiceCaseContextRecord.case_id==c.id,ServiceCaseContextRecord.context_version==c.current_context_version))
            if action=="activate" and c.status=="draft":c.status="active"
            elif action=="hold" and c.status in {"active","pending_review"}:c.status="on_hold"
            elif action=="resume" and c.status=="on_hold":c.status="active"
            elif action=="submit_review" and c.status in {"active","draft"}:
                if any(n.status not in {"completed","skipped"} for n in nodes): raise AccountStoreError(409,"WORKFLOW_NODES_INCOMPLETE","仍有未完成节点，不能提交结项审核。")
                c.status="pending_review"
            elif action=="complete" and c.status=="pending_review" and actor_role in REVIEWERS:
                p=self.project(s,organization_id,c.project_id)
                if not x or x.project_version!=p.lock_version: raise AccountStoreError(409,"WORKFLOW_CONTEXT_STALE","项目材料已更新，请刷新流程依据后再结项。")
                if (x.snapshot or {}).get("pending_items") and not acknowledge_open_items: raise AccountStoreError(409,"WORKFLOW_OPEN_ITEMS_UNACKNOWLEDGED","仍有待确认事项，请确认已处理或转入后续跟踪。")
                c.status="completed";c.completed_at=now();c.closure_summary=note
            elif action=="cancel" and c.status not in {"completed","cancelled"} and actor_role in REVIEWERS:c.status="cancelled";c.closure_summary=note
            elif action=="reopen" and c.status in {"completed","cancelled"} and actor_role in REVIEWERS:c.status="active";c.completed_at=None
            elif action in {"complete","cancel","reopen"} and actor_role not in REVIEWERS: raise AccountStoreError(403,"WORKFLOW_FORBIDDEN","只有管理员或所有者可以执行该流程操作。")
            else: raise AccountStoreError(409,"WORKFLOW_ACTION_INVALID","当前流程状态不能执行该操作。")
            c.lock_version+=1;c.updated_at=now();self.event(s,c,None,action,before,c.status,actor_user_id,actor_name,actor_role,note,{"acknowledge_open_items":acknowledge_open_items})
        return self.get(organization_id=organization_id,case_id=case_id)
    def events(self,*,organization_id,case_id):
        with self.sessions() as s:
            self.case(s,organization_id,case_id); rows=s.scalars(select(ServiceCaseEventRecord).where(ServiceCaseEventRecord.case_id==case_id).order_by(ServiceCaseEventRecord.created_at.desc())).all(); return [{"id":r.id,"case_id":r.case_id,"node_id":r.node_id,"action":r.action,"before_status":r.before_status,"after_status":r.after_status,"actor_user_id":r.actor_user_id,"actor_name":r.actor_name,"actor_role":r.actor_role,"note":r.note,"payload_sha256":r.payload_sha256,"created_at":r.created_at} for r in rows]

_STORE=None
def get_service_workflow_store():
    global _STORE
    a=get_account_store()
    if _STORE is None or _STORE.engine is not a.projects.engine:_STORE=ServiceWorkflowStore()
    return _STORE
def reset_service_workflow_store_for_tests():
    global _STORE; _STORE=None
