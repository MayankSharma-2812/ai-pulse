from tests.conftest import login


def test_login_lists_organizations(client):
    _, data = login(client, "ravi@consult.test")
    names = {o["org_name"] for o in data["organizations"]}
    assert names == {"Northwind Logistics", "Bluepeak Retail"}


def test_employee_sees_questions(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    r = client.get("/diagnostic/questions", headers=headers)
    assert r.status_code == 200
    assert any(q["id"] == "sup-drafts" for q in r.json())


def test_admin_dashboard(client):
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    org_id = data["organizations"][0]["org_id"]
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    assert len(r.json()["departments"]) == 4


def test_admin_cannot_see_other_org(client):
    _, meera_data=login(client, "meera@bluepeak.test", "Bluepeak Retail")
    other_org_id = meera_data["organizations"][0]["org_id"]

    headers, asha_data = login(client, "asha@northwind.test", "Northwind Logistics")
    asha_org_id = asha_data["organizations"][0]["org_id"]

    assert asha_org_id != other_org_id

    r=client.get(f"/dashboard?org_id={other_org_id}", headers=headers)
    assert r.status_code == 403

def test_employee_cannot_access_dashboard(client):
    headers, data = login(client, "priya@northwind.test", "Northwind Logistics")
    org_id = data["organizations"][0]["org_id"]

    r=client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 403

def test_multi_org_user_dashboard_access(client):
    nw_headers, nw_data = login(client, "ravi@consult.test", "Northwind Logistics")
    nw_org_id = next(o["org_id"] for o in nw_data["organizations"] if o["org_name"] == "Northwind Logistics")
    r_nw=client.get(f"/dashboard?org_id={nw_org_id}", headers=nw_headers)
    assert r_nw.status_code == 403  

    bp_headers, bp_data = login(client, "ravi@consult.test","Bluepeak Retail")
    bp_org_id = next(o["org_id"] for o in bp_data["organizations"] if o["org_name"] == "Bluepeak Retail")
    r_bp=client.get(f"/dashboard?org_id={bp_org_id}", headers=bp_headers)
    assert r_bp.status_code == 200