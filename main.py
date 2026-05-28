from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
import uuid
import os

app = FastAPI()

GENERATED_DIR = "generated"
os.makedirs(GENERATED_DIR, exist_ok=True)

app.mount("/generated", StaticFiles(directory=GENERATED_DIR), name="generated")


class WniosekRequest(BaseModel):
    formularz_P: Dict[str, Any]
    formularz_P1: Dict[str, Any]


@app.get("/")
def root():
    return {"status": "API działa"}


def checkbox_yes(pola, nazwa):
    pola[nazwa] = "/YES"


def checkbox_no(pola, nazwa):
    # Niektóre pola skali w tym formularzu mają wartość eksportu /No
    pola[nazwa] = "/No"


def wypelnij_pdf(szablon_pdf, plik_wynikowy, pola):
    reader = PdfReader(szablon_pdf)
    writer = PdfWriter()
    writer.append(reader)

    page = writer.pages[0]

    pola_tekstowe = {}

    for nazwa, wartosc in pola.items():
        if wartosc is None:
            wartosc = ""
        if not str(wartosc).startswith("/"):
            pola_tekstowe[nazwa] = str(wartosc)

    writer.update_page_form_field_values(page, pola_tekstowe)

    acroform = writer._root_object.get("/AcroForm")

    if acroform and "/Fields" in acroform:
        for field in acroform["/Fields"]:
            obj = field.get_object()
            name = obj.get("/T")

            if name in pola and str(pola[name]).startswith("/"):
                value = NameObject(pola[name])

                obj.update({
                    NameObject("/V"): value,
                    NameObject("/AS"): value
                })

                if "/Kids" in obj:
                    for kid in obj["/Kids"]:
                        kid_obj = kid.get_object()
                        kid_obj.update({
                            NameObject("/AS"): value
                        })

    writer.set_need_appearances_writer()

    with open(plik_wynikowy, "wb") as f:
        writer.write(f)


@app.post("/generuj-wniosek")
def generuj_wniosek(data: WniosekRequest):
    uid = str(uuid.uuid4())

    output_p = f"{GENERATED_DIR}/FormularzP_{uid}.pdf"
    output_p1 = f"{GENERATED_DIR}/FormularzP1_{uid}.pdf"

    fp = data.formularz_P
    fp1 = data.formularz_P1

    # ----------------------------
    # FORMULARZ P
    # ----------------------------

    sposob_odbioru = fp.get("sposob_odbioru", "")
    cl = fp.get("cl", "")

    pola_p = {
        "wnioskodawca_imie_nazwisko_lub_nazwa": fp.get("wnioskodawca", ""),
        "wnioskodawca_adres": fp.get("adres", ""),
        "wnioskodawca_telefon_email": fp.get("telefon_email", ""),
        "uwagi": fp.get("uwagi", ""),

        "adres_wysylki_pocztowej": fp.get("adres_wysylki", ""),

        "osoba_kontaktowa_imie_nazwisko": fp.get("osoba_kontaktowa", ""),
        "osoba_kontaktowa_email": fp.get("email_kontaktowy", ""),
        "osoba_kontaktowa_telefon": fp.get("telefon_kontaktowy", ""),

        "material_mapa_zasadnicza_lub_ewidencyjna": "/YES",
    }

    if cl == "CL1":
        checkbox_yes(pola_p, "cel_CL1_potrzeby_wlasne")
    elif cl == "CL2":
        checkbox_yes(pola_p, "cel_CL2_dowolne_potrzeby")
    elif cl == "nieodpłatne":
        checkbox_yes(pola_p, "cel_CL01")
        checkbox_yes(pola_p, "nieodplatnie_edukacyjne")

    if sposob_odbioru == "odbiór osobisty":
        checkbox_yes(pola_p, "odbior_osobisty")
    elif sposob_odbioru == "wysyłka pocztą":
        checkbox_yes(pola_p, "wysylka_pod_wskazany_adres")
    elif sposob_odbioru == "e-mail":
        checkbox_yes(pola_p, "wysylka_email")

    # ----------------------------
    # FORMULARZ P1
    # ----------------------------

    rodzaj_mapy = fp1.get("rodzaj_mapy", "")
    postac = fp1.get("postac", "")
    skala = fp1.get("skala", "")
    kolorystyka = fp1.get("kolorystyka", "")
    format_wydruku = fp1.get("format", "")

    pola_p1 = {
        "jednostka_ewidencyjna_obreb": fp1.get("obreb", ""),
        "identyfikator_dzialki_numer_dzialki": fp1.get("numer_dzialki", ""),
        "liczba_egzemplarzy": str(fp1.get("liczba_egzemplarzy", "")),
        "uwagi_P1": fp1.get("uwagi_P1", ""),
    }

    if rodzaj_mapy == "mapa zasadnicza":
        checkbox_yes(pola_p1, "mapa_zasadnicza")
    elif rodzaj_mapy == "mapa ewidencyjna":
        checkbox_yes(pola_p1, "mapa_ewidencji_gruntow_i_budynkow")

    if postac == "wektorowa":
        checkbox_yes(pola_p1, "postac_wektorowa")
    elif postac == "rastrowa":
        checkbox_yes(pola_p1, "postac_rastrowa")
    elif postac == "drukowana":
        checkbox_yes(pola_p1, "postac_drukowana")

    if skala == "1:500":
        checkbox_no(pola_p1, "skala_1_500")
    elif skala == "1:1000":
        checkbox_no(pola_p1, "skala_1_1000")
    elif skala == "1:2000":
        checkbox_no(pola_p1, "skala_1_2000")
    elif skala == "1:5000":
        checkbox_no(pola_p1, "skala_1_5000")

    if kolorystyka == "czarno-biała":
        checkbox_yes(pola_p1, "kolorystyka_czarno_biala")
    elif kolorystyka == "kolorowa":
        checkbox_yes(pola_p1, "kolorystyka_kolorowa")

    if format_wydruku == "A4":
        checkbox_yes(pola_p1, "format_A4")
    elif format_wydruku == "A3":
        checkbox_yes(pola_p1, "format_A3")
    elif format_wydruku == "A2":
        checkbox_yes(pola_p1, "format_A2")
    elif format_wydruku == "A1":
        checkbox_yes(pola_p1, "format_A1")
    elif format_wydruku == "A0":
        checkbox_yes(pola_p1, "format_A0")

    wypelnij_pdf("FormularzP.pdf", output_p, pola_p)
    wypelnij_pdf("FormularzP1.pdf", output_p1, pola_p1)

    return {
        "status": "ok",
        "pdf_P_url": f"https://api-abn7.onrender.com/generated/FormularzP_{uid}.pdf",
        "pdf_P1_url": f"https://api-abn7.onrender.com/generated/FormularzP1_{uid}.pdf"
    }
