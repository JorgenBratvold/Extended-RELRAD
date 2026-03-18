def optimal_shedding_branch_bound_trace(
    network,
    root,
    children,
    parent,
    energized_buses,
    Vmin=None,
    Vpre=None,
    capacity=None,
    fault_zone=None,
    trace=True,
):

    sections = network["sections"]
    buses = network["buses"]
    edge_lookup = network["edge_lookup"]

    best_shed = float("inf")
    best_sections_snapshot = None

    # -------------------------------------------------
    # tracing printer
    # -------------------------------------------------

    def log(depth, msg):
        if trace:
            print("│  " * depth + msg)

    # -------------------------------------------------
    # capacity check
    # -------------------------------------------------

    def capacity_ok(children_tree):

        def subtree_load(n):

            P = buses[n]["P"]

            for c in children_tree[n]:
                P += subtree_load(c)

            return P

        total_load = subtree_load(root)

        if trace:
            log(0, f"Total feeder load = {total_load:.4f} pu   Capacity = {capacity}")

        if capacity is None:
            return True

        return total_load <= capacity

    # -------------------------------------------------
    # candidate generation
    # -------------------------------------------------

    def build_candidates():

        def subtree(n):

            S = {n}

            for c in children[n]:
                S |= subtree(c)

            return S

        Candidates = {}

        for n, p in parent.items():

            sid = edge_lookup.get((p, n))
            d = sections[sid]["disc"] if sid else "N"

            if d != "N":

                T = subtree(n)

                Pc = sum(
                    buses[m]["P"] * buses[m].get("c4", 1)
                    for m in T
                )

                sec = sections[sid]

                if sec["disc"] == "U":
                    action_key = "open_up"

                elif sec["disc"] == "D":
                    action_key = "open_down"

                else:
                    action_key = (
                        "open_up"
                        if n == sec["up"]
                        else "open_down"
                    )

                Candidates[n] = {
                    "subtree": T,
                    "shed_cost": Pc,
                    "sid": sid,
                    "action_key": action_key,
                }

        for idx, c in enumerate(
            sorted(
                Candidates,
                key=lambda x: Candidates[x]["shed_cost"],
                reverse=True,
            )
        ):
            Candidates[c]["idx"] = idx

        return Candidates


    candidates = build_candidates()

    print("\n==============================")
    print("Branch & Bound restoration search")
    print("==============================")

    print(f"Number of candidates: {len(candidates)}")

    for g, c in candidates.items():
        print(
            f"Candidate bus {g+1} | "
            f"shed_cost={c['shed_cost']:.4f} | "
            f"subtree size={len(c['subtree'])}"
        )
    
    # print load per bus for each bus in candidates' subtrees
    for g, c in candidates.items():
        print(f"  - Candidate bus {g+1} subtree load details:")
        for b in sorted(c["subtree"]):
            print(f"    - Bus {b+1}: P={buses[b]['P']:.4f} pu, c4={buses[b].get('c4', 1)}, cost contribution={buses[b]['P'] * buses[b].get('c4', 1):.4f}")

    # -------------------------------------------------
    # switching operations
    # -------------------------------------------------

    def apply_candidate_switching(selected):

        changes = []

        for g in selected:

            c = candidates[g]

            sec = sections[c["sid"]]
            key = c["action_key"]

            changes.append((sec, key, sec.get(key)))

            sec[key] = True

            if trace:
                print(
                    f"   → OPEN switch on section {c['sid']} ({key})"
                )

        return changes


    def undo_changes(changes):

        for sec, key, old in reversed(changes):

            if old is None:
                sec.pop(key, None)

            else:
                sec[key] = old

    # -------------------------------------------------
    # configuration evaluation
    # -------------------------------------------------

    def evaluate_configuration(candidate_set):

        if trace:
            print(f"\nEvaluating configuration: {sorted(candidate_set)}")

        changes = apply_candidate_switching(candidate_set)

        test_energized, _, children_tree = Reachable(
            root,
            buses,
            sections,
            fault_zone=fault_zone,
        )

        if trace:
            print(
                f" Energized buses: {[b+1 for b in sorted(test_energized)]}"
            )

        feasible = True

        # capacity check

        if capacity is not None:

            if not capacity_ok(children_tree):

                if trace:
                    print(" → Capacity constraint violated")

                feasible = False

        # voltage check

        if feasible and Vmin is not None:

            V = lindistflow(
                network,
                root,
                children_tree,
                Vpre=Vpre,
            )
            print(f" Voltages: ")
            for b in sorted(test_energized):
                print(f"  - Bus {b+1}: {V[b]:.4f} pu")

            Vmin_found = min(V.values())

            if trace:
                print(f" Minimum voltage = {Vmin_found:.4f} pu")

            if Vmin_found < Vmin:

                if trace:
                    print(" → Voltage constraint violated")

                feasible = False

        snapshot = None

        if feasible:

            snapshot = {
                sid: dict(sections[sid])
                for sid in sections
            }

            if trace:
                print(" → Configuration feasible")

        else:

            if trace:
                print(" → Configuration infeasible")

        undo_changes(changes)

        return feasible, snapshot

    # -------------------------------------------------
    # Branch & Bound recursion
    # -------------------------------------------------

    def search(remaining, selected, shedset, depth):

        nonlocal best_shed
        nonlocal best_sections_snapshot

        current_shed = sum(
            candidates[g]["shed_cost"]
            for g in selected
        )

        log(depth, f"Node selected switches = {sorted(selected)}")
        log(depth, f"Current shed cost = {current_shed:.4f}")
        log(depth, f"Best known cost = {best_shed:.4f}")

        # -------------------------------------------------
        # objective pruning
        # -------------------------------------------------

        if current_shed >= best_shed:

            log(depth, "PRUNED by objective bound")

            return

        # -------------------------------------------------
        # best-case bound
        # -------------------------------------------------

        feasible, _ = evaluate_configuration(
            selected | set(remaining)
        )

        if not feasible:

            log(depth, "PRUNED by best-case infeasible")

            return

        # -------------------------------------------------
        # evaluate current solution
        # -------------------------------------------------

        feasible, snapshot = evaluate_configuration(selected)

        if feasible:

            log(depth, f"NEW BEST SOLUTION found (cost={current_shed:.4f})")

            best_shed = current_shed
            best_sections_snapshot = snapshot

            return

        log(depth, "Branching to children nodes")

        # -------------------------------------------------
        # branch
        # -------------------------------------------------

        for i, g in enumerate(remaining):

            if candidates[g]["subtree"].issubset(shedset):

                log(depth, f"Skipping candidate {g+1} (already shed)")

                continue

            log(depth, f"Branch on candidate {g+1}")

            search(
                remaining[i + 1 :],
                selected | {g},
                shedset | candidates[g]["subtree"],
                depth + 1,
            )

    ordered = sorted(
        candidates,
        key=lambda g: candidates[g]["idx"],
    )

    search(ordered, set(), set(), 0)

    print("\nSearch finished.")
    print(f"Optimal shed cost = {best_shed:.4f}")

    # -------------------------------------------------
    # apply best solution
    # -------------------------------------------------

    if best_sections_snapshot:

        for sid in sections:

            sections[sid].clear()

            sections[sid].update(
                best_sections_snapshot[sid]
            )

    final_energized, parent, children = Reachable(
        root,
        buses,
        sections,
        fault_zone=fault_zone,
    )

    shed_nodes = set(energized_buses) - set(
        final_energized
    )

    Vopt = lindistflow(
        network,
        root,
        children,
        Vpre=Vpre,
    )

    return final_energized, shed_nodes, Vopt

def simulate_mc_year_lp(args):

    (
        seed,
        buses,
        sections,
        roots,
        main_root,
        base_P,
        pv_curve,
        pv_buses,
        Sbase,
        cap_limit,
        Vmin,
        Vprefault,
        edge_lookup
    ) = args

    random.seed(seed)

    buses_local = copy.deepcopy(buses)
    sections_local = copy.deepcopy(sections)

    ENS_year = {b:0.0 for b in buses_local}

    t = 0.0

    while t < 1.0:

        events=[]

        for sid,s in sections_local.items():

            lam=s["lambda"]

            if lam<=0:
                continue

            ttf=random.expovariate(lam)
            events.append((t+ttf,sid))

        if not events:
            break

        event_time,fault_sid=min(events)

        if event_time>=1.0:
            break

        t=event_time

        hour=int((t%1)*8760)
        hour=min(hour,len(pv_curve)-1)

        r=sections_local[fault_sid]["repair_time"]
        repair=random.expovariate(1/r)/8760

        sec=copy.deepcopy(sections_local)

        for s in sec.values():
            s["fault"]=False
            s.pop("open_up",None)
            s.pop("open_down",None)

        sec[fault_sid]["fault"]=True

        fault_zone=detect_and_isolate_fault_zone(sec,buses_local)

        supplied=set()
        switch_times={}

        for root in roots:
            if cap_limit<=0 and root!=main_root:
                continue

            for b in buses_local:
                buses_local[b]["P"]=base_P[b]

            if root!=main_root:

                for bus,cap in pv_buses.items():
                    b=bus-1
                    buses_local[b]["P"]-=cap*pv_curve[hour]

            E,parent,children=Reachable(root,buses_local,sec,fault_zone)

            E=set(E)-supplied

            if not E:
                continue

            net_case={
                "buses":buses_local,
                "sections":sec,
                "edge_lookup":edge_lookup
            }

            cap=1000 if root==main_root else cap_limit

            final_E, shed_nodes =optimal_shedding_branch_bound3(
                network=net_case,
                root=root,
                children=children,
                parent=parent,
                energized_buses=E,
                Vmin=Vmin,
                Vpre=Vprefault.get(root,1.0),
                capacity=cap,
                fault_zone=fault_zone
            )

            final_E=set(final_E)

            supplied|=final_E


            Tsh=compute_island_switch_time(E,sec)

            for b in final_E:
                switch_times[b]=Tsh
        
       
        for b in buses_local:
            
            P = base_P[b]
            # PV only contributes if bus is supplied
            if (b+1) in pv_buses and b in supplied:
            
                cap = pv_buses[b+1]
                P -= cap * pv_curve[hour]
        
            P = max(P, 0) * Sbase

            #P=base_P[b]*Sbase

            if b in fault_zone:
                ENS_year[b]+=P*repair*8760

            elif b in supplied:
                ENS_year[b]+=P*switch_times.get(b,0)

            else:
                ENS_year[b]+=P*repair*8760

        t+=repair

    return ENS_year

def mc_ens_lp(
        network,
        roots,
        Vmin,
        Sbase,
        cap_limit,
        pv_curve,
        pv_buses,
        years=5000,
        beta_target=0.05,
        workers=8,
        seed=None):

    seed=seed #or int(time.time())

    buses=network["buses"]
    sections=network["sections"]

    roots=[r-1 for r in roots]
    main_root=roots[0]

    base_P={b:buses[b]["P"] for b in buses}

    _,_,children=Reachable(main_root,buses,sections)
    Vprefault, _, _ =lindistflow(network,main_root,children)

    args_list=[]

    for i in range(years):

        args_list.append((
            seed+i,
            buses,
            sections,
            roots,
            main_root,
            base_P,
            pv_curve,
            pv_buses,
            Sbase,
            cap_limit,
            Vmin,
            Vprefault,
            network["edge_lookup"]
        ))

    ENS_samples=[]
    ENS_lp_total={b:0 for b in buses}

    with ProcessPoolExecutor(max_workers=workers) as executor:

        for i,ENS_dict in enumerate(executor.map(simulate_mc_year_lp,args_list),1):

            total=sum(ENS_dict.values())
            ENS_samples.append(total)

            for b,v in ENS_dict.items():
                ENS_lp_total[b]+=v

            if i<2:
                continue

            mean=np.mean(ENS_samples)
            std=np.std(ENS_samples,ddof=1)

            beta=std/(mean*np.sqrt(i))

            if i%100==0:
                print(f"Year {i} | β={beta:.4f}")

            if beta<beta_target and i>100:
                print("\nConvergence reached")
                print("Years simulated:",i)
                break

    for b in ENS_lp_total:
        ENS_lp_total[b]/=i

    ENS_est=sum(ENS_lp_total.values())

    return ENS_est,ENS_lp_total

def run_mc_pv_scenarios(
        network,
        roots,
        Vmin,
        Sbase,
        cap_limit,
        pv_curve,
        seed = None,
        beta_target = 0.05
        ):

    results={}

    for name,pv in pv_cases.items():

        print("\nRunning scenario:",name)

        ENS_total,ENS_lp=mc_ens_lp(
            network,
            roots,
            Vmin,
            Sbase,
            cap_limit,
            pv_curve,
            pv,
            years=2000,
            seed=seed,
            beta_target=beta_target,

        )

        results[name]=ENS_lp
    
    return results

    #plot_mc_lp_pareto(results, network)

