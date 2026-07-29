--
-- PostgreSQL database dump
--

\restrict CSQuC5Y2hl1gjYhQXZ4TvZ2yxiOkV3LaigMkthjCYf9JhUj77nWcFq5UquBdIoA

-- Dumped from database version 18.4 (Debian 18.4-1.pgdg12+1)
-- Dumped by pg_dump version 18.4 (Ubuntu 18.4-1.pgdg22.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: hr_user
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO hr_user;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: employees; Type: TABLE; Schema: public; Owner: hr_user
--

CREATE TABLE public.employees (
    id integer NOT NULL,
    name character varying(150) NOT NULL,
    role character varying(100) NOT NULL,
    team_id integer,
    manager_id integer,
    start_date date NOT NULL,
    salary double precision NOT NULL,
    employment_type character varying(50) NOT NULL,
    active boolean NOT NULL
);


ALTER TABLE public.employees OWNER TO hr_user;

--
-- Name: employees_id_seq; Type: SEQUENCE; Schema: public; Owner: hr_user
--

CREATE SEQUENCE public.employees_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.employees_id_seq OWNER TO hr_user;

--
-- Name: employees_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hr_user
--

ALTER SEQUENCE public.employees_id_seq OWNED BY public.employees.id;


--
-- Name: leave_balances; Type: TABLE; Schema: public; Owner: hr_user
--

CREATE TABLE public.leave_balances (
    id integer NOT NULL,
    employee_id integer NOT NULL,
    year integer NOT NULL,
    allocated_days double precision NOT NULL,
    used_days double precision NOT NULL
);


ALTER TABLE public.leave_balances OWNER TO hr_user;

--
-- Name: leave_balances_id_seq; Type: SEQUENCE; Schema: public; Owner: hr_user
--

CREATE SEQUENCE public.leave_balances_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.leave_balances_id_seq OWNER TO hr_user;

--
-- Name: leave_balances_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hr_user
--

ALTER SEQUENCE public.leave_balances_id_seq OWNED BY public.leave_balances.id;


--
-- Name: leave_requests; Type: TABLE; Schema: public; Owner: hr_user
--

CREATE TABLE public.leave_requests (
    id integer NOT NULL,
    employee_id integer NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    days_requested double precision NOT NULL,
    status character varying(20) NOT NULL,
    is_unpaid boolean NOT NULL,
    unpaid_days double precision NOT NULL,
    flags character varying(500),
    reason character varying(500),
    requested_at timestamp without time zone NOT NULL,
    decided_at timestamp without time zone,
    decided_by character varying(150)
);


ALTER TABLE public.leave_requests OWNER TO hr_user;

--
-- Name: leave_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: hr_user
--

CREATE SEQUENCE public.leave_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.leave_requests_id_seq OWNER TO hr_user;

--
-- Name: leave_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hr_user
--

ALTER SEQUENCE public.leave_requests_id_seq OWNED BY public.leave_requests.id;


--
-- Name: payroll_runs; Type: TABLE; Schema: public; Owner: hr_user
--

CREATE TABLE public.payroll_runs (
    id integer NOT NULL,
    period_month integer NOT NULL,
    period_year integer NOT NULL,
    generated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.payroll_runs OWNER TO hr_user;

--
-- Name: payroll_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: hr_user
--

CREATE SEQUENCE public.payroll_runs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payroll_runs_id_seq OWNER TO hr_user;

--
-- Name: payroll_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hr_user
--

ALTER SEQUENCE public.payroll_runs_id_seq OWNED BY public.payroll_runs.id;


--
-- Name: payslips; Type: TABLE; Schema: public; Owner: hr_user
--

CREATE TABLE public.payslips (
    id integer NOT NULL,
    payroll_run_id integer NOT NULL,
    employee_id integer NOT NULL,
    working_days integer NOT NULL,
    unpaid_leave_days double precision NOT NULL,
    gross_pay double precision NOT NULL,
    tax_deducted double precision NOT NULL,
    social_security_deducted double precision NOT NULL,
    net_pay double precision NOT NULL
);


ALTER TABLE public.payslips OWNER TO hr_user;

--
-- Name: payslips_id_seq; Type: SEQUENCE; Schema: public; Owner: hr_user
--

CREATE SEQUENCE public.payslips_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payslips_id_seq OWNER TO hr_user;

--
-- Name: payslips_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hr_user
--

ALTER SEQUENCE public.payslips_id_seq OWNED BY public.payslips.id;


--
-- Name: teams; Type: TABLE; Schema: public; Owner: hr_user
--

CREATE TABLE public.teams (
    id integer NOT NULL,
    name character varying(100) NOT NULL
);


ALTER TABLE public.teams OWNER TO hr_user;

--
-- Name: teams_id_seq; Type: SEQUENCE; Schema: public; Owner: hr_user
--

CREATE SEQUENCE public.teams_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.teams_id_seq OWNER TO hr_user;

--
-- Name: teams_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hr_user
--

ALTER SEQUENCE public.teams_id_seq OWNED BY public.teams.id;


--
-- Name: employees id; Type: DEFAULT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.employees ALTER COLUMN id SET DEFAULT nextval('public.employees_id_seq'::regclass);


--
-- Name: leave_balances id; Type: DEFAULT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.leave_balances ALTER COLUMN id SET DEFAULT nextval('public.leave_balances_id_seq'::regclass);


--
-- Name: leave_requests id; Type: DEFAULT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.leave_requests ALTER COLUMN id SET DEFAULT nextval('public.leave_requests_id_seq'::regclass);


--
-- Name: payroll_runs id; Type: DEFAULT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.payroll_runs ALTER COLUMN id SET DEFAULT nextval('public.payroll_runs_id_seq'::regclass);


--
-- Name: payslips id; Type: DEFAULT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.payslips ALTER COLUMN id SET DEFAULT nextval('public.payslips_id_seq'::regclass);


--
-- Name: teams id; Type: DEFAULT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.teams ALTER COLUMN id SET DEFAULT nextval('public.teams_id_seq'::regclass);


--
-- Data for Name: employees; Type: TABLE DATA; Schema: public; Owner: hr_user
--

INSERT INTO public.employees VALUES (1, 'Kimberly Wangari', 'CEO', NULL, NULL, '2022-01-10', 250000, 'full_time', true);
INSERT INTO public.employees VALUES (2, 'Brian Mutiso', 'Engineering Lead', 1, 1, '2022-03-01', 180000, 'full_time', true);
INSERT INTO public.employees VALUES (3, 'Cynthia Wafula', 'Senior Software Engineer', 1, 2, '2023-06-15', 120000, 'full_time', true);
INSERT INTO public.employees VALUES (4, 'David Kiptoo', 'Junior Software Engineer', 1, 2, '2024-02-01', 50000, 'full_time', true);
INSERT INTO public.employees VALUES (5, 'Esther Nyambura', 'Ops Lead', 2, 1, '2022-05-20', 150000, 'full_time', true);
INSERT INTO public.employees VALUES (6, 'Felix Omondi', 'Ops Associate', 2, 5, '2026-07-15', 60000, 'contract', true);


--
-- Data for Name: leave_balances; Type: TABLE DATA; Schema: public; Owner: hr_user
--

INSERT INTO public.leave_balances VALUES (1, 1, 2026, 21, 0);
INSERT INTO public.leave_balances VALUES (2, 2, 2026, 21, 0);
INSERT INTO public.leave_balances VALUES (4, 4, 2026, 21, 0);
INSERT INTO public.leave_balances VALUES (5, 5, 2026, 21, 0);
INSERT INTO public.leave_balances VALUES (3, 3, 2026, 21, 5);
INSERT INTO public.leave_balances VALUES (6, 6, 2026, 21, 9);


--
-- Data for Name: leave_requests; Type: TABLE DATA; Schema: public; Owner: hr_user
--

INSERT INTO public.leave_requests VALUES (1, 3, '2026-07-10', '2026-07-14', 5, 'approved', false, 0, NULL, 'Family event', '2026-07-29 02:52:01.582986', NULL, 'Brian Mutiso');
INSERT INTO public.leave_requests VALUES (2, 4, '2026-07-30', '2026-08-01', 3, 'pending', false, 0, 'short_notice', 'Personal', '2026-07-29 02:52:01.894928', NULL, NULL);
INSERT INTO public.leave_requests VALUES (3, 6, '2026-07-20', '2026-07-31', 12, 'approved', true, 3, NULL, 'Extended leave beyond balance', '2026-07-29 02:52:02.204959', NULL, 'Esther Nyambura');


--
-- Data for Name: payroll_runs; Type: TABLE DATA; Schema: public; Owner: hr_user
--

INSERT INTO public.payroll_runs VALUES (1, 7, 2026, '2026-07-29 02:52:05.287112');


--
-- Data for Name: payslips; Type: TABLE DATA; Schema: public; Owner: hr_user
--

INSERT INTO public.payslips VALUES (1, 1, 1, 27, 0, 250000, 69783.35, 2160, 178056.65);
INSERT INTO public.payslips VALUES (2, 1, 2, 27, 0, 180000, 48783.35, 2160, 129056.65);
INSERT INTO public.payslips VALUES (3, 1, 3, 27, 0, 120000, 30783.35, 2160, 87056.65);
INSERT INTO public.payslips VALUES (4, 1, 4, 27, 0, 50000, 9783.349999999999, 2160, 38056.65);
INSERT INTO public.payslips VALUES (5, 1, 5, 27, 0, 150000, 39783.35, 2160, 108056.65);
INSERT INTO public.payslips VALUES (6, 1, 6, 27, 15, 26666.666666666664, 3066.666666666666, 1599.9999999999998, 22000);


--
-- Data for Name: teams; Type: TABLE DATA; Schema: public; Owner: hr_user
--

INSERT INTO public.teams VALUES (1, 'Engineering');
INSERT INTO public.teams VALUES (2, 'Operations');


--
-- Name: employees_id_seq; Type: SEQUENCE SET; Schema: public; Owner: hr_user
--

SELECT pg_catalog.setval('public.employees_id_seq', 6, true);


--
-- Name: leave_balances_id_seq; Type: SEQUENCE SET; Schema: public; Owner: hr_user
--

SELECT pg_catalog.setval('public.leave_balances_id_seq', 6, true);


--
-- Name: leave_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: hr_user
--

SELECT pg_catalog.setval('public.leave_requests_id_seq', 3, true);


--
-- Name: payroll_runs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: hr_user
--

SELECT pg_catalog.setval('public.payroll_runs_id_seq', 1, true);


--
-- Name: payslips_id_seq; Type: SEQUENCE SET; Schema: public; Owner: hr_user
--

SELECT pg_catalog.setval('public.payslips_id_seq', 6, true);


--
-- Name: teams_id_seq; Type: SEQUENCE SET; Schema: public; Owner: hr_user
--

SELECT pg_catalog.setval('public.teams_id_seq', 2, true);


--
-- Name: employees employees_pkey; Type: CONSTRAINT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_pkey PRIMARY KEY (id);


--
-- Name: leave_balances leave_balances_pkey; Type: CONSTRAINT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.leave_balances
    ADD CONSTRAINT leave_balances_pkey PRIMARY KEY (id);


--
-- Name: leave_requests leave_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.leave_requests
    ADD CONSTRAINT leave_requests_pkey PRIMARY KEY (id);


--
-- Name: payroll_runs payroll_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.payroll_runs
    ADD CONSTRAINT payroll_runs_pkey PRIMARY KEY (id);


--
-- Name: payslips payslips_pkey; Type: CONSTRAINT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.payslips
    ADD CONSTRAINT payslips_pkey PRIMARY KEY (id);


--
-- Name: teams teams_name_key; Type: CONSTRAINT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_name_key UNIQUE (name);


--
-- Name: teams teams_pkey; Type: CONSTRAINT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_pkey PRIMARY KEY (id);


--
-- Name: leave_balances uq_emp_year; Type: CONSTRAINT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.leave_balances
    ADD CONSTRAINT uq_emp_year UNIQUE (employee_id, year);


--
-- Name: payroll_runs uq_period; Type: CONSTRAINT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.payroll_runs
    ADD CONSTRAINT uq_period UNIQUE (period_month, period_year);


--
-- Name: employees employees_manager_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_manager_id_fkey FOREIGN KEY (manager_id) REFERENCES public.employees(id);


--
-- Name: employees employees_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id);


--
-- Name: leave_balances leave_balances_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.leave_balances
    ADD CONSTRAINT leave_balances_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: leave_requests leave_requests_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.leave_requests
    ADD CONSTRAINT leave_requests_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: payslips payslips_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.payslips
    ADD CONSTRAINT payslips_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: payslips payslips_payroll_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hr_user
--

ALTER TABLE ONLY public.payslips
    ADD CONSTRAINT payslips_payroll_run_id_fkey FOREIGN KEY (payroll_run_id) REFERENCES public.payroll_runs(id);


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: -; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON SEQUENCES TO hr_user;


--
-- Name: DEFAULT PRIVILEGES FOR TYPES; Type: DEFAULT ACL; Schema: -; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON TYPES TO hr_user;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: -; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON FUNCTIONS TO hr_user;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: -; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON TABLES TO hr_user;


--
-- PostgreSQL database dump complete
--

\unrestrict CSQuC5Y2hl1gjYhQXZ4TvZ2yxiOkV3LaigMkthjCYf9JhUj77nWcFq5UquBdIoA

