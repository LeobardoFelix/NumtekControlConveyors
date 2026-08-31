from utils.helpers import getDateTime
from db.part_tracking.part import Part
from db.part_tracking.program import Program
from db.repositories import (
    parts_repo, conveyors_repo, current_parts_repo,
    history_repo, part_numbers_repo, sequences_repo, programs_repo,
)


def load_part(part_id):
    info = parts_repo.get_information(part_id)
    #print(f"PID: {part_id} INFO: {info}")
    part = Part(part_id)
    if not info:
        print("ERROR: CAN NOT GET INFORMATION FOR THE PART")
        return part

    part.part_num = info[0][0]
    part.current_step = 0 if info[0][1] == 0 else info[0][1] - 1
    part.hanger_num = info[0][2]
    part.conveyor = info[0][3]

    programs = history_repo.get_programs_for_part(part_id)
    part.programs = [
        Program(programId, part_id, step)
        for (programId, minTime, maxTime, step, conveyor, hanger_num, state) in programs
    ]

    current_part = current_parts_repo.get_program_location(part_id)
    if (current_part and part.programs
            and current_part[0][0] == part.programs[part.current_step].program_id):
        part.programs[part.current_step].current_hanger = current_part[0][1]
        part.programs[part.current_step].current_conveyor = current_part[0][2]
    return part


def create_part(part_id, hanger_num, conveyor, part_num, start_date, start_time, order_id):
    if parts_repo.exists(part_id):
        return load_part(part_id)

    history_repo.delete(part_id)  # clear stale rows if this part_id was used before
    parts_repo.insert(part_id, hanger_num, conveyor, part_num,
                      start_date, start_time, 1, order_id)
    conveyors_repo.fill_with_order(part_id, part_num, order_id, hanger_num, conveyor)
    _init_part_in_history(part_id)

    part = load_part(part_id)
    part.updateAll()
    part.programs[part.current_step].current_hanger = hanger_num
    part.programs[part.current_step].current_conveyor = conveyor
    part.updateCurrentParts()
    return part


def delete_part(part_id, hanger_num, conveyor):
    conveyors_repo.clear(hanger_num, conveyor)
    parts_repo.delete(part_id)
    current_parts_repo.delete(part_id)
    fecha, hora = getDateTime()
    history_repo.mark_last_step_done(fecha, part_id)


def _init_part_in_history(part_id):
    """Seed the history table with one row per program in the part's sequence."""
    part = parts_repo.get_history_init_info(part_id)[0]
    part_num, start_date, start_time, hanger_id, hanger_num, conveyor, order_id = part
    sequenceID = part_numbers_repo.get_sequence_id(part_num)[0][0]
    programs = sequences_repo.get_programs(sequenceID)
    for i, (program_id, min_drying, max_drying, step) in enumerate(programs):
        robot_num, conveyor_start, conveyor_end = programs_repo.get_robot_and_conveyors(program_id)[0]
        history_repo.insert_step(
            part_id, part_num, step, program_id, robot_num,
            min_drying, max_drying, conveyor_start, conveyor_end, order_id, start_date,
        )
        if i == 0:
            history_repo.set_first_step_ready(conveyor, hanger_num, program_id, part_id)
