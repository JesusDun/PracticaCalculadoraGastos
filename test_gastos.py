# test_gastos.py
import pytest

def test_suma_gastos_basica():
    # Prueba dummy para validar que el pipeline de GitHub Actions funciona
    gasto_alimentos = 250.00
    gasto_transporte = 50.00
    total = gasto_alimentos + gasto_transporte
    
    assert total == 300.00
