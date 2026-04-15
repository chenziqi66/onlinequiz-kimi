from django.shortcuts import render,redirect,reverse
from . import forms,models
from django.db.models import Sum
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required,user_passes_test
from django.conf import settings
from datetime import date, timedelta
from quiz import models as QMODEL
from teacher import models as TMODEL


#for showing signup/login button for student
def studentclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request,'student/studentclick.html')

def student_signup_view(request):
    userForm=forms.StudentUserForm()
    studentForm=forms.StudentForm()
    mydict={'userForm':userForm,'studentForm':studentForm}
    if request.method=='POST':
        userForm=forms.StudentUserForm(request.POST)
        studentForm=forms.StudentForm(request.POST,request.FILES)
        if userForm.is_valid() and studentForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            student=studentForm.save(commit=False)
            student.user=user
            student.save()
            my_student_group = Group.objects.get_or_create(name='STUDENT')
            my_student_group[0].user_set.add(user)
        return HttpResponseRedirect('studentlogin')
    return render(request,'student/studentsignup.html',context=mydict)

def is_student(user):
    return user.groups.filter(name='STUDENT').exists()

@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def student_dashboard_view(request):
    dict={
    
    'total_course':QMODEL.Course.objects.all().count(),
    'total_question':QMODEL.Question.objects.all().count(),
    }
    return render(request,'student/student_dashboard.html',context=dict)

@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def student_exam_view(request):
    courses=QMODEL.Course.objects.all()
    return render(request,'student/student_exam.html',{'courses':courses})

@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def take_exam_view(request,pk):
    course=QMODEL.Course.objects.get(id=pk)
    total_questions=QMODEL.Question.objects.all().filter(course=course).count()
    questions=QMODEL.Question.objects.all().filter(course=course)
    total_marks=0
    for q in questions:
        total_marks=total_marks + q.marks
    
    return render(request,'student/take_exam.html',{'course':course,'total_questions':total_questions,'total_marks':total_marks})

@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def start_exam_view(request,pk):
    course=QMODEL.Course.objects.get(id=pk)
    questions=QMODEL.Question.objects.all().filter(course=course)
    if request.method=='POST':
        pass
    response= render(request,'student/start_exam.html',{'course':course,'questions':questions})
    response.set_cookie('course_id',course.id)
    return response


@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def calculate_marks_view(request):
    if request.COOKIES.get('course_id') is not None:
        course_id = request.COOKIES.get('course_id')
        course=QMODEL.Course.objects.get(id=course_id)
        
        total_marks=0
        wrong_answers=[]
        questions=QMODEL.Question.objects.all().filter(course=course)
        for i in range(len(questions)):
            
            selected_ans = request.COOKIES.get(str(i+1))
            actual_answer = questions[i].answer
            if selected_ans == actual_answer:
                total_marks = total_marks + questions[i].marks
            else:
                wrong_answers.append({
                    'question': questions[i],
                    'student_answer': selected_ans if selected_ans else '未作答'
                })
        student = models.Student.objects.get(user_id=request.user.id)
        result = QMODEL.Result()
        result.marks=total_marks
        result.exam=course
        result.student=student
        result.save()
        
        request.session['wrong_answers'] = wrong_answers
        request.session['course_id'] = course_id
        request.session['total_marks'] = total_marks

        return HttpResponseRedirect('view-result')



@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def view_result_view(request):
    courses=QMODEL.Course.objects.all()
    return render(request,'student/view_result.html',{'courses':courses})
    

@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def check_marks_view(request,pk):
    course=QMODEL.Course.objects.get(id=pk)
    student = models.Student.objects.get(user_id=request.user.id)
    results= QMODEL.Result.objects.all().filter(exam=course).filter(student=student)
    return render(request,'student/check_marks.html',{'results':results})

@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def student_marks_view(request):
    courses=QMODEL.Course.objects.all()
    return render(request,'student/student_marks.html',{'courses':courses})

@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def view_wrong_answers_view(request):
    wrong_answers = request.session.get('wrong_answers', [])
    course_id = request.session.get('course_id')
    total_marks = request.session.get('total_marks', 0)
    course = None
    if course_id:
        course = QMODEL.Course.objects.get(id=course_id)
    return render(request, 'student/view_wrong_answers.html', {
        'wrong_answers': wrong_answers,
        'course': course,
        'total_marks': total_marks
    })

@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def add_to_wrong_answer_book_view(request):
    wrong_answers = request.session.get('wrong_answers', [])
    course_id = request.session.get('course_id')
    student = models.Student.objects.get(user_id=request.user.id)
    
    if course_id and wrong_answers:
        course = QMODEL.Course.objects.get(id=course_id)
        for wa in wrong_answers:
            question = wa['question']
            student_answer = wa['student_answer']
            QMODEL.WrongAnswer.objects.get_or_create(
                student=student,
                question=question,
                defaults={
                    'exam': course,
                    'student_answer': student_answer
                }
            )
    
    return redirect('wrong-answer-book')

@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def wrong_answer_book_view(request):
    student = models.Student.objects.get(user_id=request.user.id)
    wrong_answers = QMODEL.WrongAnswer.objects.filter(student=student).select_related('question', 'exam')
    
    total_count = wrong_answers.count()
    
    course_stats = {}
    for wa in wrong_answers:
        course_name = wa.exam.course_name
        if course_name in course_stats:
            course_stats[course_name] += 1
        else:
            course_stats[course_name] = 1
    
    recent_wrong_answers = wrong_answers.order_by('-date')[:10]
    
    return render(request, 'student/wrong_answer_book.html', {
        'total_count': total_count,
        'course_stats': course_stats,
        'recent_wrong_answers': recent_wrong_answers
    })

@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def wrong_answer_detail_view(request, pk):
    wrong_answer = QMODEL.WrongAnswer.objects.select_related('question', 'exam').get(id=pk)
    return render(request, 'student/wrong_answer_detail.html', {
        'wrong_answer': wrong_answer
    })
  