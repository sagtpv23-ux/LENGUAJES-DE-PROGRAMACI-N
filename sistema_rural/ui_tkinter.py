"""Interfaz gráfica orientada a eventos (sílabo, Tema 5: eventos, listeners, handlers y GUI).

Cómo se evitan las fallas comunes de una interfaz (ver docs/guia_silabo.md):
1. Validar datos: el ControladorSistema valida antes de registrar y avisa del error.
2. Asociar eventos: cada botón tiene command= con su handler (_al_...).
3. No bloquear la interfaz: las operaciones son instantáneas (se midió 0,002 s), así que se
   muestra "Procesando..." y se actualiza la ventana; no hace falta trabajar en segundo plano.
4. Manejar excepciones: todo handler pasa por _ejecutar(), que usa try/except.
5. Separar interfaz y lógica: esta clase solo dibuja y captura acciones; la lógica está en
   el ControladorSistema y en el dominio.
6. Dar retroalimentación: la barra inferior muestra éxito (verde), error (rojo) o alerta (naranja).
7. Sincronizar datos: las tablas se vuelven a llenar desde el registro central cuando llega
   un evento del BusEventos (listeners).
8. Confirmar acciones críticas: eliminar y cancelar piden confirmación (askyesno).
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .controlador import ControladorSistema
from .excepciones import ErrorSistemaRural
from .validaciones import (permitir_dni, permitir_fecha, permitir_hora, permitir_largo, permitir_nombre,
                           permitir_nombre_medicamento, permitir_numero)

AZUL, AZUL_CLARO, ROJO_CLARO, VERDE_CLARO = "#1F4E79", "#DDEBF7", "#FADBD8", "#D5F5E3"
COLOR_EXITO, COLOR_ERROR, COLOR_ALERTA = "#1E8449", "#B03A2E", "#CA6F1E"


class VentanaPrincipal(tk.Tk):
    def __init__(self, nombre_establecimiento="Centro de Salud Rural «Santa Rosa»"):
        super().__init__()
        self.title("SistemaRural-PE - Gestión de establecimiento de salud")
        self.geometry("980x640")
        self.minsize(860, 560)
        self._ctrl = ControladorSistema()
        self._opts_pac, self._opts_per = [], []
        # Filtros de escritura: se evalúan en cada tecla y bloquean lo que no se permite
        # (por ejemplo, el DNI acepta solo números y deja de escribir al llegar a 8 dígitos).
        self._v_dni = (self.register(permitir_dni), "%P")
        self._v_nombre = (self.register(permitir_nombre), "%P")
        self._v_fecha = (self.register(permitir_fecha), "%P")
        self._v_hora = (self.register(permitir_hora), "%P")
        self._v_cantidad = (self.register(lambda texto: permitir_numero(texto, 6)), "%P")
        self._v_motivo = (self.register(lambda texto: permitir_largo(texto, 100)), "%P")
        self._v_colegiatura = (self.register(lambda texto: permitir_largo(texto, 20)), "%P")
        self._v_medicamento = (self.register(permitir_nombre_medicamento), "%P")
        self._configurar_estilo()
        self._crear_encabezado(nombre_establecimiento)
        self._pestañas = ttk.Notebook(self)
        self._pestañas.pack(fill="both", expand=True, padx=10, pady=(8, 0))
        self._crear_pestaña_pacientes()
        self._crear_pestaña_personal()
        self._crear_pestaña_citas()
        self._crear_pestaña_inventario()
        self._crear_pestaña_reportes()
        # Barra de estado: muestra el resultado de cada acción (retroalimentación al usuario)
        self._estado = tk.StringVar(value="Listo.")
        self._lbl_estado = tk.Label(self, textvariable=self._estado, anchor="w", bg="#F2F2F2",
                                    relief="sunken", font=("Segoe UI", 10, "bold"))
        self._lbl_estado.pack(fill="x", side="bottom")
        self._suscribir_eventos()
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)   # evento: el usuario cierra la ventana
        self._refrescar_todo()

    # ---------- construcción de la interfaz ----------
    def _configurar_estilo(self):
        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure("Treeview", rowheight=24)
        estilo.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background=AZUL_CLARO)
        estilo.configure("TNotebook.Tab", padding=(16, 6), font=("Segoe UI", 10, "bold"))
        estilo.configure("Accion.TButton", font=("Segoe UI", 10, "bold"), padding=6)

    def _crear_encabezado(self, nombre):
        marco = tk.Frame(self, bg=AZUL)
        marco.pack(fill="x")
        tk.Label(marco, text="SistemaRural-PE", bg=AZUL, fg="white", font=("Segoe UI", 18, "bold")).pack(
            side="left", padx=14, pady=8)
        tk.Label(marco, text=nombre, bg=AZUL, fg="#D6E4F0", font=("Segoe UI", 11)).pack(side="left")
        ttk.Button(marco, text="Cargar datos de demostración", command=self._al_cargar_demo).pack(
            side="right", padx=14)

    @staticmethod
    def _tabla(padre, columnas, anchos, alto=10):
        marco = ttk.Frame(padre)
        arbol = ttk.Treeview(marco, columns=columnas, show="headings", height=alto, selectmode="browse")
        for col, ancho in zip(columnas, anchos):
            arbol.heading(col, text=col)
            arbol.column(col, width=ancho, anchor="w")
        barra = ttk.Scrollbar(marco, orient="vertical", command=arbol.yview)
        arbol.configure(yscrollcommand=barra.set)
        arbol.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        return marco, arbol

    def _crear_pestaña_pacientes(self):
        pagina = ttk.Frame(self._pestañas, padding=10)
        self._pestañas.add(pagina, text="  Pacientes  ")
        formulario = ttk.LabelFrame(pagina, text="Registrar paciente", padding=10)
        formulario.pack(fill="x")
        self._pac = {}
        campos = (("DNI (8 dígitos)", 12, self._v_dni), ("Nombres", 18, self._v_nombre),
                  ("Apellidos", 20, self._v_nombre), ("Nacimiento (AAAA-MM-DD)", 14, self._v_fecha))
        for col, (etiqueta, ancho, filtro) in enumerate(campos):
            ttk.Label(formulario, text=etiqueta).grid(row=0, column=col, sticky="w", padx=4)
            entrada = ttk.Entry(formulario, width=ancho, validate="key", validatecommand=filtro)
            entrada.grid(row=1, column=col, padx=4, pady=2)
            self._pac[etiqueta] = entrada
        ttk.Button(formulario, text="Registrar", style="Accion.TButton",
                   command=self._al_registrar_paciente).grid(row=1, column=4, padx=10)
        busqueda = ttk.Frame(pagina)
        busqueda.pack(fill="x", pady=(10, 4))
        ttk.Label(busqueda, text="Buscar por DNI:").pack(side="left")
        self._busqueda = ttk.Entry(busqueda, width=14, validate="key", validatecommand=self._v_dni)
        self._busqueda.pack(side="left", padx=6)
        ttk.Button(busqueda, text="Buscar", command=self._al_buscar_paciente).pack(side="left")
        ttk.Button(busqueda, text="Ver todos", command=self._refrescar_pacientes).pack(side="left", padx=6)
        ttk.Button(busqueda, text="Eliminar paciente seleccionado", command=self._al_eliminar_paciente).pack(
            side="left", padx=12)
        self._total_pac = tk.StringVar()
        ttk.Label(busqueda, textvariable=self._total_pac).pack(side="right")
        marco, self._arbol_pac = self._tabla(pagina, ("DNI", "Paciente", "Edad"), (140, 420, 80), 12)
        marco.pack(fill="both", expand=True)

    def _crear_pestaña_personal(self):
        pagina = ttk.Frame(self._pestañas, padding=10)
        self._pestañas.add(pagina, text="  Personal  ")
        formulario = ttk.LabelFrame(pagina, text="Registrar personal de salud", padding=10)
        formulario.pack(fill="x")
        ttk.Label(formulario, text="Tipo").grid(row=0, column=0, sticky="w", padx=4)
        self._cb_tipo = ttk.Combobox(formulario, state="readonly", width=12, values=self._ctrl.tipos_personal())
        self._cb_tipo.grid(row=1, column=0, padx=4, pady=2)
        self._per = {}
        campos = (("DNI (8 dígitos)", 12, self._v_dni), ("Nombres", 18, self._v_nombre),
                  ("Apellidos", 20, self._v_nombre), ("Colegiatura (ej. CMP-00001)", 18, self._v_colegiatura))
        for col, (etiqueta, ancho, filtro) in enumerate(campos, start=1):
            ttk.Label(formulario, text=etiqueta).grid(row=0, column=col, sticky="w", padx=4)
            entrada = ttk.Entry(formulario, width=ancho, validate="key", validatecommand=filtro)
            entrada.grid(row=1, column=col, padx=4, pady=2)
            self._per[etiqueta] = entrada
        ttk.Button(formulario, text="Registrar personal", style="Accion.TButton",
                   command=self._al_registrar_personal).grid(row=1, column=5, padx=10)
        marco, self._arbol_per = self._tabla(
            pagina, ("DNI", "Nombre", "Cargo", "Colegiatura"), (130, 360, 110, 160), 12)
        marco.pack(fill="both", expand=True, pady=(10, 0))

    def _crear_pestaña_citas(self):
        pagina = ttk.Frame(self._pestañas, padding=10)
        self._pestañas.add(pagina, text="  Citas  ")
        formulario = ttk.LabelFrame(pagina, text="Programar cita", padding=10)
        formulario.pack(fill="x")
        ttk.Label(formulario, text="Paciente").grid(row=0, column=0, sticky="w", padx=4)
        ttk.Label(formulario, text="Profesional").grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(formulario, text="Fecha (AAAA-MM-DD)").grid(row=0, column=2, sticky="w", padx=4)
        ttk.Label(formulario, text="Hora (HH:MM)").grid(row=0, column=3, sticky="w", padx=4)
        ttk.Label(formulario, text="Motivo").grid(row=2, column=0, sticky="w", padx=4)
        self._cb_pac = ttk.Combobox(formulario, state="readonly", width=32)
        self._cb_per = ttk.Combobox(formulario, state="readonly", width=26)
        self._cita_fecha = ttk.Entry(formulario, width=14, validate="key", validatecommand=self._v_fecha)
        self._cita_hora = ttk.Entry(formulario, width=8, validate="key", validatecommand=self._v_hora)
        self._cita_motivo = ttk.Entry(formulario, width=60, validate="key", validatecommand=self._v_motivo)
        self._cb_pac.grid(row=1, column=0, padx=4, pady=2)
        self._cb_per.grid(row=1, column=1, padx=4, pady=2)
        self._cita_fecha.grid(row=1, column=2, padx=4, pady=2)
        self._cita_hora.grid(row=1, column=3, padx=4, pady=2)
        self._cita_motivo.grid(row=3, column=0, columnspan=3, sticky="w", padx=4, pady=2)
        ttk.Button(formulario, text="Programar", style="Accion.TButton",
                   command=self._al_programar_cita).grid(row=3, column=3, padx=4)
        acciones = ttk.Frame(pagina)
        acciones.pack(fill="x", pady=(10, 4))
        ttk.Button(acciones, text="Marcar como atendida", command=self._al_atender).pack(side="left")
        ttk.Button(acciones, text="Cancelar cita", command=self._al_cancelar).pack(side="left", padx=6)
        ttk.Button(acciones, text="Eliminar cita", command=self._al_eliminar_cita).pack(side="left", padx=6)
        marco, self._arbol_citas = self._tabla(
            pagina, ("N.°", "Fecha y hora", "Paciente", "Profesional", "Estado"), (50, 140, 280, 250, 100), 12)
        marco.pack(fill="both", expand=True)
        self._arbol_citas.tag_configure("atendida", background=VERDE_CLARO)
        self._arbol_citas.tag_configure("cancelada", background="#EAEDED", foreground="#7B7D7D")

    def _crear_pestaña_inventario(self):
        pagina = ttk.Frame(self._pestañas, padding=10)
        self._pestañas.add(pagina, text="  Inventario  ")
        nuevo = ttk.LabelFrame(pagina, text="Registrar medicamento nuevo", padding=10)
        nuevo.pack(fill="x", pady=(0, 10))
        ttk.Label(nuevo, text="Nombre (ej. Paracetamol 500 mg)").grid(row=0, column=0, sticky="w", padx=4)
        ttk.Label(nuevo, text="Stock inicial").grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(nuevo, text="Stock mínimo").grid(row=0, column=2, sticky="w", padx=4)
        self._med_nombre = ttk.Entry(nuevo, width=34, validate="key", validatecommand=self._v_medicamento)
        self._med_stock = ttk.Entry(nuevo, width=10, validate="key", validatecommand=self._v_cantidad)
        self._med_minimo = ttk.Entry(nuevo, width=10, validate="key", validatecommand=self._v_cantidad)
        self._med_nombre.grid(row=1, column=0, padx=4, pady=2)
        self._med_stock.grid(row=1, column=1, padx=4, pady=2)
        self._med_minimo.grid(row=1, column=2, padx=4, pady=2)
        ttk.Button(nuevo, text="Registrar medicamento", style="Accion.TButton",
                   command=self._al_agregar_medicamento).grid(row=1, column=3, padx=10)
        marco, self._arbol_inv = self._tabla(
            pagina, ("Medicamento", "Stock", "Mínimo", "Estado"), (340, 90, 90, 120), 12)
        marco.pack(fill="both", expand=True)
        self._arbol_inv.tag_configure("critico", background=ROJO_CLARO, foreground="#922B21")
        acciones = ttk.LabelFrame(pagina, text="Movimiento de stock del medicamento seleccionado", padding=10)
        acciones.pack(fill="x", pady=(10, 0))
        ttk.Label(acciones, text="Profesional:").pack(side="left")
        self._cb_dispensa = ttk.Combobox(acciones, state="readonly", width=30)
        self._cb_dispensa.pack(side="left", padx=6)
        ttk.Label(acciones, text="Cantidad:").pack(side="left")
        self._cantidad = ttk.Entry(acciones, width=8, validate="key", validatecommand=self._v_cantidad)
        self._cantidad.pack(side="left", padx=6)
        ttk.Button(acciones, text="Dispensar", style="Accion.TButton", command=self._al_dispensar).pack(
            side="left", padx=4)
        ttk.Button(acciones, text="Reponer", command=self._al_reponer).pack(side="left", padx=4)

    def _crear_pestaña_reportes(self):
        pagina = ttk.Frame(self._pestañas, padding=10)
        self._pestañas.add(pagina, text="  Reportes  ")
        barra = ttk.Frame(pagina)
        barra.pack(fill="x")
        ttk.Button(barra, text="Generar reporte", style="Accion.TButton", command=self._al_generar_reporte).pack(
            side="left")
        ttk.Button(barra, text="Exportar respaldo cifrado…", command=self._al_exportar).pack(side="left", padx=8)
        self._texto = tk.Text(pagina, height=20, font=("Consolas", 10), state="disabled", bg="#FBFCFC")
        self._texto.pack(fill="both", expand=True, pady=(10, 0))

    # ---------- eventos del dominio (Observer) ----------
    def _suscribir_eventos(self):
        bus = self._ctrl.registro.eventos
        bus.suscribir("paciente_registrado", self._evento_datos)
        bus.suscribir("paciente_eliminado", self._evento_datos)
        bus.suscribir("personal_registrado", self._evento_datos)
        bus.suscribir("cita_programada", self._evento_datos)
        bus.suscribir("cita_actualizada", self._evento_datos)
        bus.suscribir("inventario_actualizado", self._evento_datos)
        bus.suscribir("stock_bajo", self._evento_stock_bajo)

    def _evento_datos(self, **_datos):
        self._refrescar_todo()

    def _evento_stock_bajo(self, medicamento, stock):
        self._mostrar(f"ALERTA: stock crítico de {medicamento} ({stock} u.).", COLOR_ALERTA)
        messagebox.showwarning("Stock crítico", f"{medicamento} quedó con {stock} unidades.")

    # ---------- refresco de tablas ----------
    @staticmethod
    def _llenar(arbol, filas, etiqueta=None, ids=None):
        """Borra la tabla y la vuelve a llenar con los datos actuales del registro central."""
        for fila_vieja in arbol.get_children():
            arbol.delete(fila_vieja)
        for k, fila in enumerate(filas):
            tags = (etiqueta(fila),) if etiqueta else ()
            if ids:
                arbol.insert("", "end", iid=ids[k], values=fila, tags=tags)
            else:
                arbol.insert("", "end", values=fila, tags=tags)

    def _refrescar_pacientes(self):
        con_id = self._ctrl.filas_pacientes(con_id=True)
        filas = [fila for _, fila in con_id]
        self._llenar(self._arbol_pac, filas, ids=[i for i, _ in con_id])
        self._total_pac.set(f"{len(filas)} paciente(s) registrado(s)")

    def _refrescar_todo(self):
        self._refrescar_pacientes()
        self._opts_pac, self._opts_per = self._ctrl.opciones_pacientes(), self._ctrl.opciones_personal()
        self._llenar(self._arbol_per, self._ctrl.filas_personal())
        self._cb_pac["values"] = [e for e, _ in self._opts_pac]
        self._cb_per["values"] = [e for e, _ in self._opts_per]
        self._cb_dispensa["values"] = [e for e, _ in self._opts_per]
        self._llenar(self._arbol_citas, self._ctrl.filas_citas(), lambda f: f[4])
        self._llenar(self._arbol_inv, self._ctrl.filas_inventario(), lambda f: "critico" if f[3] == "CRÍTICO" else "")

    # ---------- handlers de acciones del usuario ----------
    def _mostrar(self, mensaje, color=COLOR_EXITO):
        """Retroalimentación: escribe el mensaje en la barra de estado con su color."""
        self._estado.set(mensaje)
        self._lbl_estado.configure(fg=color)

    def _ejecutar(self, accion, mensaje_ok=""):
        """Ejecuta una acción del usuario capturando los errores (try/except)."""
        try:
            accion()
            if mensaje_ok:
                self._mostrar(mensaje_ok, COLOR_EXITO)
        except (ErrorSistemaRural, ValueError) as error:
            self._mostrar(f"Error: {error}", COLOR_ERROR)
            messagebox.showerror("No se pudo completar la acción", str(error))

    def _al_registrar_paciente(self):
        c = {k: v.get() for k, v in self._pac.items()}

        def registrar():
            self._ctrl.registrar_paciente(c["DNI (8 dígitos)"], c["Nombres"], c["Apellidos"], c["Nacimiento (AAAA-MM-DD)"])
            for entrada in self._pac.values():
                entrada.delete(0, tk.END)
        self._ejecutar(registrar, "Paciente registrado.")

    def _al_registrar_personal(self):
        c = {k: v.get() for k, v in self._per.items()}

        def registrar():
            self._ctrl.registrar_personal(self._cb_tipo.get(), c["DNI (8 dígitos)"], c["Nombres"], c["Apellidos"],
                                          c["Colegiatura (ej. CMP-00001)"])
            for entrada in self._per.values():
                entrada.delete(0, tk.END)
            self._cb_tipo.set("")
        self._ejecutar(registrar, "Personal registrado.")

    def _al_agregar_medicamento(self):
        def agregar():
            self._ctrl.agregar_medicamento(self._med_nombre.get(), self._med_stock.get(), self._med_minimo.get())
            for entrada in (self._med_nombre, self._med_stock, self._med_minimo):
                entrada.delete(0, tk.END)
        self._ejecutar(agregar, "Medicamento registrado.")

    def _al_buscar_paciente(self):
        def buscar():
            con_id = self._ctrl.filas_pacientes(self._busqueda.get(), con_id=True)
            self._llenar(self._arbol_pac, [f for _, f in con_id], ids=[i for i, _ in con_id])
        self._ejecutar(buscar, "Búsqueda realizada.")

    def _al_programar_cita(self):
        def programar():
            i, j = self._cb_pac.current(), self._cb_per.current()
            paciente = self._opts_pac[i][1] if i >= 0 else None
            personal = self._opts_per[j][1] if j >= 0 else None
            self._ctrl.programar_cita(paciente, personal, self._cita_fecha.get(), self._cita_hora.get(),
                                      self._cita_motivo.get())
            self._cita_motivo.delete(0, tk.END)
        self._ejecutar(programar, "Cita programada.")

    def _al_eliminar_paciente(self):
        def eliminar():
            seleccion = self._arbol_pac.selection()
            if not seleccion:
                raise ErrorSistemaRural("Seleccione un paciente de la tabla.")
            nombre = self._arbol_pac.item(seleccion[0], "values")[1]
            # Acción crítica: se pide confirmación antes de borrar
            if messagebox.askyesno("Confirmar eliminación",
                                   f"¿Eliminar a {nombre} y todo su historial de citas?\nEsta acción no se puede deshacer."):
                self._ctrl.eliminar_paciente(seleccion[0])
                self._mostrar("Paciente eliminado.", COLOR_EXITO)
        self._ejecutar(eliminar)

    def _al_eliminar_cita(self):
        def eliminar():
            id_cita = self._id_cita_seleccionada()
            if messagebox.askyesno("Confirmar eliminación", f"¿Eliminar la cita {id_cita}? No se puede deshacer."):
                self._ctrl.eliminar_cita(id_cita)
                self._mostrar("Cita eliminada.", COLOR_EXITO)
        self._ejecutar(eliminar)

    def _id_cita_seleccionada(self) -> int:
        seleccion = self._arbol_citas.selection()
        if not seleccion:
            raise ErrorSistemaRural("Seleccione una cita de la tabla.")
        return int(self._arbol_citas.item(seleccion[0], "values")[0])

    def _al_atender(self):
        self._ejecutar(lambda: self._ctrl.atender_cita(self._id_cita_seleccionada()), "Cita marcada como atendida.")

    def _al_cancelar(self):
        def cancelar():
            id_cita = self._id_cita_seleccionada()
            if messagebox.askyesno("Confirmar cancelación", f"¿Cancelar la cita {id_cita}?"):
                self._ctrl.cancelar_cita(id_cita)
                self._mostrar("Cita cancelada.", COLOR_EXITO)
        self._ejecutar(cancelar)

    def _medicamento_seleccionado(self) -> str:
        seleccion = self._arbol_inv.selection()
        if not seleccion:
            raise ErrorSistemaRural("Seleccione un medicamento de la tabla.")
        return self._arbol_inv.item(seleccion[0], "values")[0]

    def _al_dispensar(self):
        def dispensar():
            j = self._cb_dispensa.current()
            if j < 0:
                raise ErrorSistemaRural("Seleccione el profesional que dispensa.")
            profesional = self._opts_per[j][1]      # solo el médico tiene permiso (RF5)
            self._ctrl.dispensar(self._medicamento_seleccionado(), self._cantidad.get(), profesional)
        self._ejecutar(dispensar, "Medicamento dispensado.")

    def _al_reponer(self):
        self._ejecutar(lambda: self._ctrl.reponer(self._medicamento_seleccionado(), self._cantidad.get()),
                       "Stock repuesto.")

    def _al_generar_reporte(self):
        def generar():
            self._mostrar("Procesando...", COLOR_ALERTA)
            self.update_idletasks()               # dibuja el aviso antes de empezar
            texto = self._ctrl.texto_reporte()
            self._texto.configure(state="normal")
            self._texto.delete("1.0", tk.END)
            self._texto.insert(tk.END, texto)
            self._texto.configure(state="disabled")
        self._ejecutar(generar, "Reporte generado (sin datos sensibles).")

    def _al_exportar(self):
        ruta = filedialog.asksaveasfilename(title="Guardar respaldo cifrado", defaultextension=".bin",
                                            filetypes=[("Respaldo cifrado", "*.bin")])
        if not ruta:
            return

        def exportar():
            self._mostrar("Procesando...", COLOR_ALERTA)
            self.update_idletasks()
            clave = self._ctrl.exportar_respaldo(ruta)
            messagebox.showinfo("Respaldo creado",
                                "Guarde esta clave en un lugar seguro; sin ella no se puede abrir el archivo:\n\n" + clave)
        self._ejecutar(exportar, "Respaldo cifrado exportado.")

    def _al_cerrar(self):
        """Handler del cierre: avisa si hay datos sin registrar o sin guardar antes de salir."""
        if any(entrada.get().strip() for entrada in self._pac.values()):
            if not messagebox.askyesno("Datos sin registrar",
                                       "Hay datos escritos en el formulario de pacientes que aún no se registraron.\n\n"
                                       "¿Desea salir de todos modos?"):
                return
        if self._ctrl.hay_cambios_sin_guardar:
            decision = messagebox.askyesnocancel(
                "Cambios sin guardar",
                "Hay cambios que aún no se han guardado.\n\n"
                "¿Desea guardar los cambios antes de salir?\n"
                "Sí: exportar el respaldo cifrado.   No: salir sin guardar.   Cancelar: volver al programa.")
            if decision is None:
                return
            if decision:
                self._al_exportar()
                if self._ctrl.hay_cambios_sin_guardar:   # canceló el guardado o hubo un error
                    return
        self.destroy()

    def _al_cargar_demo(self):
        self._ejecutar(self._ctrl.cargar_demo, "Datos de demostración cargados (ficticios).")


if __name__ == "__main__":
    VentanaPrincipal().mainloop()
